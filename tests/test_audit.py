import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('audit', Path(__file__).parents[1] / 'scripts/audit_foundation.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout

    def init(self):
        if not shutil.which('git'):
            self.skipTest('Git not installed')
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob('*') if p.is_file()}

    def test_empty_project_stays_empty(self):
        result = module.audit(self.root)
        self.assertFalse(any(result['layout_suggestions'].values()))
        self.assertEqual([], list(self.root.iterdir()))

    def test_missing_project_rejected(self):
        with self.assertRaises(ValueError):
            module.audit(self.root / 'missing')

    def test_unicode_links_and_missing_target(self):
        (self.root / 'docs').mkdir()
        (self.root / 'docs/事实 文件.md').write_text('已确认', encoding='utf-8')
        (self.root / 'README.md').write_text(
            '[事实](<docs/事实 文件.md>)\n[错](docs/missing.md)\n'
            '[网](https://example.invalid)\n[节](#section)\n'
            '```text\n[示例](not-a-real-file)\n```\n', encoding='utf-8')
        result = module.audit(self.root)
        self.assertEqual([{'document': 'README.md', 'target': 'docs/missing.md'}],
                         result['broken_local_links'])

    def test_dirty_repo_no_mutation_or_secret_output(self):
        self.init()
        (self.root / 'README.md').write_text('before', encoding='utf-8')
        self.git('add', 'README.md')
        self.git('commit', '-m', 'fixture')
        (self.root / 'README.md').write_text('after', encoding='utf-8')
        (self.root / '.env').write_text('TOKEN=sentinel-private-value', encoding='utf-8')
        before = self.snapshot()
        result = module.audit(self.root)
        self.assertEqual(before, self.snapshot())
        self.assertIn('README.md', result['git']['root']['changes'])
        self.assertNotIn('sentinel-private-value', str(result))
        self.assertEqual('main', result['git']['root']['branch'])

    def test_ancestor_repository_detected(self):
        self.init()
        sub = self.root / 'nested'
        sub.mkdir()
        self.assertEqual('ancestor', module.audit(sub)['git']['root']['git_marker'])

    def test_linked_worktree_detected(self):
        self.init()
        (self.root / 'README.md').write_text('fixture', encoding='utf-8')
        self.git('add', 'README.md')
        self.git('commit', '-m', 'fixture')
        self.git('worktree', 'add', '-b', 'task', str(self.root / 'src'))
        before = self.snapshot()
        result = module.audit(self.root)
        self.assertEqual('file', result['git']['src']['git_marker'])
        self.assertEqual('task', result['git']['src']['branch'])
        self.assertEqual(before, self.snapshot())

    def test_git_unavailable_not_reported_as_success(self):
        with patch.object(module.shutil, 'which', return_value=None):
            self.assertEqual('git_unavailable', module.audit(self.root)['git']['root']['status'])

    def test_invalid_utf8_marked_unreadable(self):
        (self.root / 'README.md').write_bytes(b'\xff\xfe\x00')
        self.assertEqual(['README.md'], module.audit(self.root)['unreadable_documents'])


if __name__ == '__main__':
    unittest.main()
