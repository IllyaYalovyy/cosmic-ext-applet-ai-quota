"""Exercise the actual Git hooks and version checker in disposable repositories."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parent.parent
META = 'data/io.github.illyayalovyy.cosmic-ext-applet-ai-quota.metainfo.xml'
FILES = ('Cargo.toml', 'Cargo.lock', 'CHANGELOG.md', META,
         'scripts/check-version.py', 'scripts/install-git-hooks.sh')
AUTHOR = 'Illya Yalovyy'
EMAIL = '1623643+IllyaYalovyy@users.noreply.github.com'


class ReleasePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ai-quota-policy-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = os.environ | {
            'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': str(self.root / 'isolated-global-config'),
            'GIT_AUTHOR_NAME': AUTHOR, 'GIT_AUTHOR_EMAIL': EMAIL,
            'GIT_COMMITTER_NAME': AUTHOR, 'GIT_COMMITTER_EMAIL': EMAIL,
        }
        self.original = {name: (ROOT / name).read_text() for name in FILES}
        self.base = tomllib.loads(self.original['Cargo.toml'])['package']['version']
        for name in FILES:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        self.run_command('git', 'init', '-b', 'main')
        self.run_command('git', 'config', 'user.name', AUTHOR)
        self.run_command('git', 'config', 'user.email', EMAIL)
        inherited = self.root / 'inherited-hooks'
        inherited.mkdir()
        hook = inherited / 'commit-msg'
        hook.write_text('#!/bin/sh\n! grep -q inherited-policy-deny "$1"\n')
        hook.chmod(0o755)
        self.run_command('git', 'config', '--global', 'core.hooksPath', str(inherited))
        self.run_command('./scripts/install-git-hooks.sh')
        self.stage()
        self.run_command('git', 'commit', '-m', 'test: initial policy fixture')
        self.run_command('./scripts/check-version.py', '--commit')

    def run_command(self, *args, success=True, env=None):
        result = subprocess.run(args, cwd=self.root, env=env or self.env,
                                text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=15)
        self.assertEqual(result.returncode == 0, success, result.stdout)
        return result.stdout

    def stage(self):
        self.run_command('git', 'add', *FILES)

    def set_version(self, version):
        for name in ('Cargo.toml', 'Cargo.lock', 'CHANGELOG.md', META):
            text = self.original[name]
            if name == 'Cargo.lock':
                before = f'name = "cosmic-ext-applet-ai-quota"\nversion = "{self.base}"'
                text = text.replace(before, before.replace(self.base, version), 1)
            else:
                text = text.replace(self.base, version, 1)
            (self.root / name).write_text(text)

    def patch_version(self):
        major, minor, patch = map(int, self.base.split('.'))
        return f'{major}.{minor}.{patch + 1}'

    def test_accepts_patch_minor_and_major_bumps(self):
        major, minor, patch = map(int, self.base.split('.'))
        for version in (f'{major}.{minor}.{patch + 1}', f'{major}.{minor + 1}.0', f'{major + 1}.0.0'):
            with self.subTest(version=version):
                self.set_version(version)
                self.stage()
                self.run_command('./scripts/check-version.py', '--staged')

    def test_rejects_unchanged_version_for_documentation_commit(self):
        (self.root / 'CHANGELOG.md').write_text(self.original['CHANGELOG.md'] + '\nMore documentation.\n')
        self.stage()
        self.run_command('git', 'commit', '-m', 'test: unchanged version', success=False)

    def test_rejects_skipped_and_malformed_versions(self):
        major, minor, patch = map(int, self.base.split('.'))
        for version in ('0.0.0', '01.2.3', '1.2', f'{major}.{minor}.{patch + 2}'):
            with self.subTest(version=version):
                self.set_version(version)
                self.stage()
                self.run_command('./scripts/check-version.py', '--staged', success=False)

    def test_rejects_each_inconsistent_metadata_file(self):
        for name in ('Cargo.lock', 'CHANGELOG.md', META):
            with self.subTest(file=name):
                self.set_version(self.patch_version())
                (self.root / name).write_text(self.original[name])
                self.stage()
                self.run_command('./scripts/check-version.py', '--staged', success=False)

    def test_checks_staged_metadata_not_unstaged_version(self):
        self.set_version(self.patch_version())
        self.run_command('./scripts/check-version.py')
        self.run_command('./scripts/check-version.py', '--staged', success=False)

    def test_rejects_wrong_author_without_creating_a_commit(self):
        self.set_version(self.patch_version())
        self.stage()
        self.run_command('.git/hooks/pre-commit', success=False,
                         env=self.env | {'GIT_AUTHOR_NAME': 'Wrong', 'GIT_AUTHOR_EMAIL': 'wrong@example.invalid'})

    def test_rejects_coauthor_trailers_and_preserves_inherited_guard(self):
        self.run_command('./scripts/install-git-hooks.sh')  # idempotent, keeps global guard
        message = self.root / 'message'
        for text in ('test\n\nCo-Authored-By: Wrong <wrong@example.invalid>\n',
                     'test: inherited-policy-deny\n'):
            message.write_text(text)
            self.run_command('.git/hooks/commit-msg', str(message), success=False)
        message.write_text('test: sole-author message\n')
        self.run_command('.git/hooks/commit-msg', str(message))

    def test_valid_commit_runs_all_hooks(self):
        self.set_version(self.patch_version())
        self.stage()
        self.run_command('git', 'commit', '-m', 'test: valid patch')
        self.run_command('./scripts/check-version.py', '--commit')
        self.assertEqual(self.run_command('git', 'log', '-1', '--format=%an <%ae>').strip(),
                         f'{AUTHOR} <{EMAIL}>')


if __name__ == '__main__':
    unittest.main()
