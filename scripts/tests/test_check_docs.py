"""Regression tests use isolated temporary repositories, never production services."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_docs import validate
from doc_facts import fingerprint


class DocumentationChecksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write('docs/README.md', '# Index\n[Guide](guide.md)\n')
        self.write('docs/guide.md', '# Guide\n')

    def write(self, name, text):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def guide(self, text):
        self.write('docs/guide.md', '# Guide\n' + text)
        return validate(self.root)

    def test_valid_links_and_unicode_duplicate_anchors(self):
        report = self.guide('## 한국어 제목\n## 한국어 제목\n[link](#한국어-제목-1)\n')
        self.assertTrue(report['ok'], report)

    def test_missing_link_and_anchor_are_failures(self):
        for target in ['missing.md', '#missing']:
            with self.subTest(target=target):
                self.assertFalse(self.guide(f'[link]({target})')['ok'])

    def test_link_in_fence_is_not_checked(self):
        self.assertTrue(self.guide('```md\n[example](missing.md)\n```\n')['ok'])

    def test_reference_links_and_external_skips(self):
        report = self.guide('[ok][guide]\n[guide]: README.md\n[remote](https://example.invalid)\n')
        self.assertTrue(report['ok'], report)
        self.assertEqual(report['counts']['external_links_skipped'], 1)
        self.assertFalse(self.guide('[bad][missing]')['ok'])

    def test_inline_link_examples_and_extension_names_are_not_references(self):
        report = self.guide('`[label][id]` and `[label](missing.md)` use `.py` files')
        self.assertTrue(report['ok'], report)

    def test_path_escape_is_rejected(self):
        self.assertFalse(self.guide('[outside](../../outside.md)')['ok'])

    def test_symlink_outside_repository_is_rejected(self):
        (self.root/'docs/outside').symlink_to(self.root.parent, target_is_directory=True)
        self.assertFalse(self.guide('[outside](outside)')['ok'])

    def test_code_paths_and_globs(self):
        self.write('apps/api/app/domain/status.py', 'value = 1\n')
        self.assertTrue(self.guide('`domain/*.py`')['ok'])
        self.assertFalse(self.guide('`domain/missing.py`')['ok'])

    def test_make_npm_commands_and_cwd(self):
        self.write('Makefile', 'check:\n\ttrue\n')
        self.write('apps/web/package.json', '{"scripts":{"build":"never executed"}}')
        report = self.guide('```sh\nmake check\ncd apps/web && npm run build\n```\n')
        self.assertTrue(report['ok'], report)
        self.assertFalse(self.guide('```sh\nmake missing\n```')['ok'])
        report = self.guide('<!-- doc-cwd: apps/web -->\n```sh\nnpm run missing\n```')
        self.assertFalse(report['ok'])

    def test_unsupported_shell_is_not_executed(self):
        marker = self.root/'must-not-exist'
        report = self.guide(f'```sh\ntouch {marker}\n```')
        self.assertTrue(report['ok'], report)
        self.assertEqual(report['counts']['commands_skipped'], 1)
        self.assertFalse(marker.exists())

    def test_python_file_target(self):
        self.write('scripts/run.py', 'raise RuntimeError("must not execute")')
        self.assertTrue(self.guide('```sh\npython3 scripts/run.py\n```')['ok'])
        self.assertFalse(self.guide('```sh\npython3 scripts/missing.py\n```')['ok'])

    def test_missing_symbol_and_invalid_directive(self):
        self.write('code.py', 'def exists():\n    pass\n')
        fact = dict(kind='symbol', path='code.py', symbol='missing')
        self.assertFalse(self.guide(f'<!-- doc-check: {json.dumps(fact)} -->')['ok'])
        self.assertFalse(self.guide('<!-- doc-check: {broken} -->')['ok'])
        self.assertFalse(self.guide('<!-- doc-check: [] -->')['ok'])
        self.assertFalse(self.guide('<!-- doc-check: {} -->')['ok'])

    def test_changed_fingerprint_requires_review_but_formatting_does_not(self):
        path = self.write('code.py', 'def example():\n    return 1\n')
        fact = dict(kind='review', path='code.py', symbol='example', sha256=fingerprint(path, 'example'))
        directive = f'<!-- doc-check: {json.dumps(fact)} -->'
        self.assertTrue(self.guide(directive)['ok'])
        path.write_text('# comment\ndef example():\n  return 1\n')
        self.assertTrue(self.guide(directive)['ok'])
        path.write_text('def example():\n    return 2\n')
        report = self.guide(directive)
        self.assertFalse(report['ok'])
        self.assertIn('REVIEW required', report['errors'][0]['message'])

    def test_toml_value_and_enum_are_checked(self):
        self.write('project.toml', '[project]\nrequires-python = ">=3.11"\n')
        fact = dict(kind='toml', path='project.toml', key='project.requires-python', expected='>=3.11')
        self.assertTrue(self.guide(f'<!-- doc-check: {json.dumps(fact)} -->')['ok'])
        fact['expected'] = '>=3.12'
        self.assertFalse(self.guide(f'<!-- doc-check: {json.dumps(fact)} -->')['ok'])
        self.write('state.py', 'class State:\n    READY = "READY"\n')
        fact = dict(kind='enum', path='state.py', symbol='State', expected={'READY': 'READY'})
        self.assertTrue(self.guide(f'<!-- doc-check: {json.dumps(fact)} -->')['ok'])
        fact['expected']['DONE'] = 'DONE'
        self.assertFalse(self.guide(f'<!-- doc-check: {json.dumps(fact)} -->')['ok'])

    def test_unclosed_fence_and_oversized_document_fail(self):
        self.assertFalse(self.guide('```sh\nmake check')['ok'])
        self.assertFalse(self.guide('\n' * 300)['ok'])


if __name__ == '__main__':
    unittest.main()
