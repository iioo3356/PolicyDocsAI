"""Check repository-owned files without inspecting secrets or generated output."""
import ast
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"package-lock.json", "next-env.d.ts"}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".yml", ".yaml", ".css", ".toml"}


def check_python(path: Path, text: str) -> list[str]:
    tree = ast.parse(text)
    errors = []
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    if len(classes) > 1:
        errors.append(f"one class per file required: {len(classes)} classes")
    relative = path.relative_to(ROOT).as_posix()
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        for module in modules:
            head = module.split('.')[0]
            if relative.startswith("apps/api/app/domain/"):
                local = isinstance(node, ast.ImportFrom) and node.level > 0
                if not local and head not in sys.stdlib_module_names and not module.startswith("app.domain"):
                    errors.append(f"domain dependency forbidden: {module}")
            if relative.startswith("apps/api/app/application/") and head in {"fastapi", "starlette"}:
                errors.append(f"application HTTP dependency forbidden: {module}")
            if relative.startswith("apps/api/app/presentation/routes/"):
                if module == "sqlalchemy" or module.startswith("app.infrastructure.models"):
                    errors.append(f"route persistence dependency forbidden: {module}")
    return errors


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, check=True, capture_output=True,
    )
    failures = []
    checked = 0
    for name in sorted(set(result.stdout.decode().split('\0')) - {""}):
        path = ROOT / name
        if not path.is_file() or path.name in EXCLUDED:
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {"Makefile", "Dockerfile"}:
            continue
        text = path.read_text()
        checked += 1
        errors = []
        count = len(text.splitlines())
        if count > 300:
            errors.append(f"{count} lines (maximum 300)")
        if path.suffix == '.py':
            errors.extend(check_python(path, text))
        if path.suffix in {'.ts', '.tsx', '.js', '.jsx'}:
            classes = re.findall(r'^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+\w+', text, re.M)
            if len(classes) > 1:
                errors.append("one class per file required")
            types = re.findall(r'^(?:export\s+)?(?:type|interface)\s+\w+', text, re.M)
            if len(types) > 1:
                errors.append("one named data type per file required")
        failures.extend(f"{name}: {error}" for error in errors)
    print('\n'.join(failures) if failures else f"Development rules passed ({checked} files).")
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
