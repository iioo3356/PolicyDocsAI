"""Offline documentation checks. No application import, network, or command execution."""
import argparse
import json
from pathlib import Path
import re
import sys

from doc_facts import check_fact, fingerprint, parse_fact, repository_path
from doc_markdown import check_code_path, check_command, check_link, outside_fences

ROOT = Path(__file__).resolve().parents[1]


def validate(root: Path) -> dict:
    errors = []
    counts = dict(documents=0, links=0, code_paths=0, commands=0, facts=0,
                  external_links_skipped=0, commands_skipped=0)
    documents = sorted((root/'docs').rglob('*.md'))
    if not documents:
        errors.append({'file': 'docs', 'line': 1, 'message': 'no Markdown documents found'})
    for document in documents:
        counts['documents'] += 1
        relative = str(document.relative_to(root))

        def attempt(number, operation):
            try:
                return operation()
            except (ValueError, OSError, KeyError, TypeError, SyntaxError) as exc:
                errors.append({'file': relative, 'line': number, 'message': str(exc)})
                return None

        text = document.read_text(encoding='utf-8')
        if len(text.splitlines()) > 300:
            errors.append({'file': relative, 'line': 301, 'message': 'maximum 300 lines exceeded'})
        prose = attempt(1, lambda: list(outside_fences(text))) or []
        definitions = {}
        for number, line in prose:
            match = re.match(r'^\s*\[([^]]+)\]:\s*(\S+)', line)
            if match:
                definitions[match[1].casefold()] = match[2]
        for number, line in prose:
            if 'doc-check:' in line:
                match = re.fullmatch(r'\s*<!-- doc-check: (.+) -->\s*', line)
                if not match:
                    errors.append({'file': relative, 'line': number, 'message': 'invalid doc-check syntax'})
                else:
                    attempt(number, lambda: check_fact(root, parse_fact(match[1])))
                    counts['facts'] += 1
                continue
            link_text = re.sub(r'`[^`]*`', '', line)
            for target in re.findall(r'\[[^]]*\]\(([^)]+)\)', link_text):
                result = attempt(number, lambda: check_link(root, document, target))
                counts['links' if result else 'external_links_skipped'] += result is not None
            for label, key in re.findall(r'\[([^]]+)\]\[([^]]*)\]', link_text):
                target = definitions.get((key or label).casefold())
                if target is None:
                    errors.append({'file': relative, 'line': number, 'message': f'undefined link reference: {key or label}'})
                else:
                    result = attempt(number, lambda: check_link(root, document, target))
                    counts['links' if result else 'external_links_skipped'] += result is not None
            for value in re.findall(r'(?<!`)`([^`]+)`(?!`)', line):
                result = attempt(number, lambda: check_code_path(root, document, value))
                counts['code_paths'] += bool(result)
        fence = None
        shell = False
        pending_cwd = root
        cwd = root
        for number, line in enumerate(text.splitlines(), 1):
            context = re.fullmatch(r'<!-- doc-cwd: (.+) -->', line)
            if fence is None and context:
                pending_cwd = attempt(number, lambda: repository_path(root, context[1])) or root
                continue
            marker = re.match(r'^\s{0,3}(`{3,}|~{3,})(.*)$', line)
            if marker:
                if fence is None:
                    fence = marker[1]
                    shell = marker[2].strip() in {'sh', 'bash', 'shell'}
                    cwd, pending_cwd = pending_cwd, root
                elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                    fence, shell = None, False
                continue
            if shell:
                result = attempt(number, lambda: check_command(root, cwd, line))
                if result:
                    cwd, checked, skipped = result
                    counts['commands'] += checked
                    counts['commands_skipped'] += skipped
    return {'ok': not errors, 'counts': counts, 'errors': errors,
            'scope': 'Static evidence only; prose meaning and runtime behavior are not proven.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='machine-readable compact report')
    parser.add_argument('--fingerprint', metavar='PATH', help='print AST fingerprint for reviewed evidence')
    parser.add_argument('--symbol', default='', help='Python symbol for --fingerprint; omit for entire file')
    args = parser.parse_args()
    if args.fingerprint:
        try:
            print(fingerprint(repository_path(ROOT, args.fingerprint), args.symbol))
            return 0
        except (ValueError, OSError, SyntaxError) as exc:
            parser.error(str(exc))
    report = validate(ROOT)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, separators=(',', ':')))
    else:
        for error in report['errors'][:20]:
            print(f"{error['file']}:{error['line']}: {error['message']}")
        remaining = len(report['errors']) - 20
        if remaining > 0:
            print(f'{remaining} more errors; use --json for all details')
        print(f"Docs {'PASS' if report['ok'] else 'FAIL'}: "
              + ', '.join(f'{key}={value}' for key, value in report['counts'].items()))
        print(report['scope'])
    return int(not report['ok'])


if __name__ == '__main__':
    sys.exit(main())
