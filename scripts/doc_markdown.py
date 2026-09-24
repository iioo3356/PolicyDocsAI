"""Small validator for the Markdown and shell examples used in this repository."""
import json
from pathlib import Path
import re
import shlex
from urllib.parse import unquote, urlsplit

from doc_facts import repository_path


def outside_fences(text: str):
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r'^\s{0,3}(`{3,}|~{3,})(.*)$', line)
        if match:
            marker, tail = match.groups()
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence) and not tail.strip():
                fence = None
            continue
        if fence is None:
            yield number, line
    if fence is not None:
        raise ValueError('unclosed fenced code block')


def anchors(text: str) -> set[str]:
    found = set()
    for _, line in outside_fences(text):
        match = re.match(r'^#{1,6}\s+(.+?)(?:\s+#+)?\s*$', line)
        if not match:
            continue
        title = re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', match[1]).lower()
        base = re.sub(r'[^\w\- ]', '', title).replace(' ', '-')
        name = base
        index = 0
        while name in found:
            index += 1
            name = f'{base}-{index}'
        found.add(name)
    return found


def check_link(root: Path, document: Path, target: str):
    target = target.strip('<>')
    url = urlsplit(target)
    if url.scheme in {'http', 'https', 'mailto'}:
        return False
    if url.scheme or url.netloc:
        raise ValueError(f'unsupported link scheme: {target}')
    path = document if not url.path else document.parent / unquote(url.path)
    path = repository_path(root, str(path))
    if url.fragment and path.suffix == '.md':
        if unquote(url.fragment) not in anchors(path.read_text(encoding='utf-8')):
            raise ValueError(f'missing Markdown heading: {target}')
    return True


def check_code_path(root: Path, document: Path, value: str) -> bool:
    if re.fullmatch(r'\.[a-z]+', value):
        return False
    if not re.fullmatch(r'[\w./*\-]+', value):
        return False
    if not (value.endswith(('.py', '.ts', '.tsx', '.toml', '.json', '.md', '/'))):
        return False
    bases = [root, document.parent, root/'apps/api/app', root/'apps/api/tests', root/'apps/web']
    candidates = set()
    for base in bases:
        if '*' in value:
            candidates.update(p.resolve() for p in base.glob(value))
        else:
            path = base/value
            if path.exists():
                candidates.add(path.resolve())
    if not candidates:
        raise ValueError(f'missing code path: {value}')
    if any(not p.is_relative_to(root.resolve()) for p in candidates):
        raise ValueError(f'code path escapes repository: {value}')
    if len(candidates) > 1 and '*' not in value:
        raise ValueError(f'ambiguous code path (use repository-relative path): {value}')
    return True


def check_command(root: Path, cwd: Path, line: str):
    """Return (new cwd, validated commands, unsupported commands); never execute."""
    words = shlex.split(line, comments=True)
    if not words:
        return cwd, 0, 0
    if '&&' in words:
        split = words.index('&&')
        cwd, valid, skipped = check_command(root, cwd, shlex.join(words[:split]))
        cwd, more, other = check_command(root, cwd, shlex.join(words[split+1:]))
        return cwd, valid + more, skipped + other
    if words[0] == 'cd' and len(words) == 2:
        target = repository_path(root, str(cwd/words[1]))
        if not target.is_dir():
            raise ValueError(f'not a directory: {words[1]}')
        return target, 1, 0
    if words[0] == 'make':
        targets = set(re.findall(r'^([\w-]+)\s*:', (cwd/'Makefile').read_text(), re.M))
        requested = words[1:]
        if not requested or any(word not in targets for word in requested):
            raise ValueError(f'unknown/unsupported make target: {line}')
    elif words[:2] == ['npm', 'run'] and len(words) >= 3:
        package = json.loads((cwd/'package.json').read_text())
        if words[2] not in package.get('scripts', {}):
            raise ValueError(f'unknown npm script: {words[2]}')
    elif words[0] in {'python', 'python3', 'pytest'}:
        for word in words[1:]:
            if word.endswith('.py') or '.py::' in word:
                repository_path(root, str(cwd/word.split('::')[0]))
        # Interpreter/module availability and arbitrary Python code are not validated.
        if not any(word.endswith('.py') for word in words[1:]):
            return cwd, 0, 1
    else:
        return cwd, 0, 1
    return cwd, 1, 0
