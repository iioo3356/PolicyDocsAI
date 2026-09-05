import posixpath
import re
from collections import deque


CODE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
CONFIG_NAMES = {
    "api.ts", "api.tsx", "api.js", "api.jsx",
    "client.ts", "client.tsx", "client.js", "client.jsx",
    "config.ts", "config.tsx", "config.js", "config.jsx",
    "env.ts", "env.js", "constants.ts", "constants.js",
}
CONFIG_PARTS = {"config", "configs", "generated", "__generated__"}
IMPORT_PATTERN = re.compile(
    r"(?:import|export)\s+(?:[\s\S]*?\s+from\s+)?[\"']([^\"']+)[\"']"
    r"|(?:import|require)\s*\(\s*[\"']([^\"']+)[\"']\s*\)"
)


def _is_config_file(path: str) -> bool:
    parts = path.split("/")
    return parts[-1].lower() in CONFIG_NAMES or bool(CONFIG_PARTS.intersection(part.lower() for part in parts))


def _is_route_entry(path: str) -> bool:
    lower = path.lower()
    name = lower.rsplit("/", 1)[-1]
    in_src = lower.startswith("src/") or "/src/" in lower
    app_route = ("/app/" in f"/{lower}" and name in {"page.ts", "page.tsx", "page.js", "page.jsx"})
    pages_route = "/pages/" in f"/{lower}" and "/pages/api/" not in f"/{lower}" and not name.startswith("_")
    explicit_router = in_src and name in {
        "app.ts", "app.tsx", "app.js", "app.jsx", "routes.ts", "routes.tsx", "routes.js", "routes.jsx",
        "router.ts", "router.tsx", "router.js", "router.jsx", "main.ts", "main.tsx", "main.js", "main.jsx",
    }
    return app_route or pages_route or explicit_router


def _src_root(path: str) -> str | None:
    parts = path.split("/")
    try:
        index = parts.index("src")
    except ValueError:
        return None
    return "/".join(parts[:index + 1])


def _resolve_import(importer: str, specifier: str, available: set[str]) -> str | None:
    if specifier.startswith("."):
        base = posixpath.normpath(posixpath.join(posixpath.dirname(importer), specifier))
    elif specifier.startswith(("@/", "~/")):
        root = _src_root(importer)
        if not root:
            return None
        base = posixpath.join(root, specifier[2:])
    else:
        return None

    candidates = [base]
    candidates.extend(base + extension for extension in CODE_EXTENSIONS)
    candidates.extend(posixpath.join(base, "index" + extension) for extension in CODE_EXTENSIONS)
    return next((candidate for candidate in candidates if candidate in available), None)


def select_reachable_react_files(documents: list[tuple[str, bytes]]) -> tuple[list[tuple[str, bytes]], dict]:
    """Keep route-reachable React files; fall back to all files when no React route entry exists."""
    normalized = [(posixpath.normpath(path.replace("\\", "/")).lstrip("./"), raw) for path, raw in documents]
    by_path = {path: raw for path, raw in normalized}
    available = set(by_path)
    entries = sorted(path for path in available if _is_route_entry(path) and not _is_config_file(path))
    if not entries:
        return normalized, {"mode": "all-code-fallback", "entries": 0, "selected": len(normalized), "ignored": 0}

    reachable: set[str] = set()
    queue = deque(entries)
    while queue:
        path = queue.popleft()
        if path in reachable or _is_config_file(path):
            continue
        reachable.add(path)
        text = by_path[path].decode("utf-8", errors="replace")
        for match in IMPORT_PATTERN.finditer(text):
            dependency = _resolve_import(path, match.group(1) or match.group(2), available)
            if dependency and dependency not in reachable and not _is_config_file(dependency):
                queue.append(dependency)

    selected = [(path, by_path[path]) for path in sorted(reachable)]
    return selected, {
        "mode": "route-reachable",
        "entries": len(entries),
        "selected": len(selected),
        "ignored": len(normalized) - len(selected),
    }
