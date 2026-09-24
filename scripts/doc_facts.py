"""Validate explicit documentation evidence without importing application code."""
import ast
import hashlib
import json
from pathlib import Path
import tomllib


def repository_path(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes repository: {value}")
    if not path.exists():
        raise ValueError(f"missing path: {value}")
    return path


def symbol_node(path: Path, symbol: str):
    node = ast.parse(path.read_text(encoding="utf-8"))
    if symbol:
        for part in symbol.split('.'):
            node = next((child for child in getattr(node, 'body', [])
                         if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                         and child.name == part), None)
            if node is None:
                raise ValueError(f"missing Python symbol: {symbol}")
    return node


def fingerprint(path: Path, symbol: str = "") -> str:
    node = symbol_node(path, symbol)
    canonical = ast.dump(node, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def check_fact(root: Path, fact: dict) -> None:
    kind = fact.get('kind')
    schemas = {
        'symbol': {'kind', 'path', 'symbol'},
        'review': {'kind', 'path', 'symbol', 'sha256'},
        'toml': {'kind', 'path', 'key', 'expected'},
        'enum': {'kind', 'path', 'symbol', 'expected'},
    }
    if kind not in schemas or set(fact) != schemas[kind]:
        raise ValueError(f"invalid doc-check fields/kind: {kind}")
    path = repository_path(root, fact['path'])
    if kind == 'toml':
        value = tomllib.loads(path.read_text(encoding="utf-8"))
        for key in fact['key'].split('.'):
            value = value[key]
        if value != fact['expected']:
            raise ValueError(f"TOML {fact['key']} changed: expected {fact['expected']!r}, got {value!r}")
        return
    node = symbol_node(path, fact['symbol'])
    if kind == 'enum':
        if not isinstance(node, ast.ClassDef):
            raise ValueError('enum evidence must reference a class')
        actual = {}
        for member in node.body:
            if isinstance(member, ast.Assign):
                for target in member.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith('_'):
                        actual[target.id] = ast.literal_eval(member.value)
        if actual != fact['expected']:
            raise ValueError(f"enum members changed: {fact['symbol']} = {actual!r}")
    if kind == 'review':
        actual = fingerprint(path, fact['symbol'])
        if actual != fact['sha256']:
            raise ValueError(
                f"REVIEW required: {fact['path']}::{fact['symbol']} changed; "
                "review the related prose before updating its fingerprint"
            )


def parse_fact(text: str) -> dict:
    fact = json.loads(text)
    if not isinstance(fact, dict):
        raise ValueError('doc-check must be a JSON object')
    return fact
