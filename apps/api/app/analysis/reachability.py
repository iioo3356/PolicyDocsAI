import posixpath
import re
from collections import deque

from tree_sitter import Node
from tree_sitter_language_pack import get_parser


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
LANGUAGE_BY_EXTENSION = {
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
}


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


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _string_value(node: Node, source: bytes) -> str | None:
    if node.type not in {"string", "string_fragment"}:
        return None
    value = _node_text(node, source)
    if node.type == "string" and len(value) >= 2 and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _first_string(node: Node, source: bytes) -> str | None:
    pending = [node]
    while pending:
        current = pending.pop()
        value = _string_value(current, source)
        if value is not None:
            return value
        pending.extend(reversed(current.children))
    return None


def _call_name(node: Node, source: bytes) -> str:
    function = node.child_by_field_name("function")
    return _node_text(function, source) if function else ""


def _ast_imports(path: str, source: bytes) -> set[str]:
    """Extract static imports, re-exports, require(), and import() using tree-sitter."""
    extension = posixpath.splitext(path)[1].lower()
    parser = get_parser(LANGUAGE_BY_EXTENSION[extension])
    root = parser.parse(source).root_node
    imports: set[str] = set()
    pending = [root]

    while pending:
        node = pending.pop()
        if node.type in {"import_statement", "export_statement"}:
            source_node = node.child_by_field_name("source")
            specifier = _string_value(source_node, source) if source_node else None
            if specifier:
                imports.add(specifier)
        elif node.type == "call_expression" and _call_name(node, source) in {"require", "import"}:
            arguments = node.child_by_field_name("arguments")
            specifier = _first_string(arguments, source) if arguments else None
            if specifier:
                imports.add(specifier)
        pending.extend(reversed(node.children))

    return imports


def _import_specifiers(path: str, source: bytes) -> set[str]:
    try:
        return _ast_imports(path, source)
    except Exception:
        # A malformed/unsupported source file must not abort the whole analysis job.
        text = source.decode("utf-8", errors="replace")
        return {match.group(1) or match.group(2) for match in IMPORT_PATTERN.finditer(text)}


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
        for specifier in _import_specifiers(path, by_path[path]):
            dependency = _resolve_import(path, specifier, available)
            if dependency and dependency not in reachable and not _is_config_file(dependency):
                queue.append(dependency)

    selected = [(path, by_path[path]) for path in sorted(reachable)]
    return selected, {
        "mode": "route-reachable",
        "entries": len(entries),
        "selected": len(selected),
        "ignored": len(normalized) - len(selected),
    }
