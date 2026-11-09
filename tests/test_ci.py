"""Offline regression tests for commit selection and guarded publication."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SHA = 'a' * 40
OTHER = 'b' * 40


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


plan = load('ci-plan')
publisher = load('ci-publish')


class PlanTests(unittest.TestCase):
    def test_push_includes_intermediate_commits_in_order(self):
        with patch.object(plan, 'git', return_value=OTHER + '\n' + SHA) as git, \
                patch.object(plan.subprocess, 'run'):
            self.assertEqual(plan.commits_for_event('push', {'before': 'c' * 40}, SHA), [OTHER, SHA])
            self.assertIn('--first-parent', git.call_args.args)
            self.assertIn('--reverse', git.call_args.args)

    def test_pr_uses_actual_head_not_merge_commit(self):
        self.assertEqual(plan.commits_for_event('pull_request', {'pull_request': {'head': {'sha': OTHER}}}, SHA), [OTHER])

    def test_new_branch_and_dispatch_use_tip(self):
        self.assertEqual(plan.commits_for_event('push', {'before': '0' * 40}, SHA), [SHA])
        self.assertEqual(plan.commits_for_event('workflow_dispatch', {}, SHA), [SHA])

    def test_invalid_shas_are_rejected(self):
        with self.assertRaises(ValueError):
            plan.commits_for_event('push', {'before': '--all'}, SHA)

    def test_oversized_push_is_not_silently_truncated(self):
        with patch.object(plan, 'git', return_value='\n'.join([SHA] * 257)), \
                patch.object(plan.subprocess, 'run'), self.assertRaises(ValueError):
            plan.commits_for_event('push', {'before': OTHER}, SHA)


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ai-quota-ci-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Cargo.toml').write_text('[package]\nversion="0.2.0"\n')
        (self.root / 'CHANGELOG.md').write_text('# Changelog\n\n## 0.2.0 — date\n\n- Tests.\n')
        self.rpm = self.root / 'cosmic-ext-applet-ai-quota-0.2.0-1.fc45.x86_64.rpm'
        self.rpm.write_bytes(b'tested package')
        self.digest = hashlib.sha256(self.rpm.read_bytes()).hexdigest()
        (self.root / 'SHA256SUMS').write_text(f'{self.digest}  ./{self.rpm.name}\n')
        self.tag_sha = None
        self.release = None
        self.latest = None
        self.main_sha = SHA
        self.upload_bad_digest = False
        self.commands = []
        for target in [patch.object(publisher, 'ROOT', self.root),
                       patch.object(publisher, 'api', side_effect=self.api),
                       patch.object(publisher, 'gh', side_effect=self.gh),
                       patch.object(publisher.subprocess, 'check_output', return_value=SHA + '\n')]:
            target.start()
            self.addCleanup(target.stop)

    def asset(self):
        return {'name': self.rpm.name, 'size': self.rpm.stat().st_size,
                'digest': 'sha256:' + self.digest, 'state': 'uploaded'}

    def api(self, path, payload=None, missing=False):
        if '/git/ref/tags/' in path:
            return {'object': {'sha': self.tag_sha}} if self.tag_sha else None
        if path.endswith('/git/refs'):
            self.tag_sha = payload['sha']
            return {}
        if '/commits/v' in path:
            return {'sha': self.tag_sha}
        if path.endswith('/commits/main'):
            return {'sha': self.main_sha}
        if '/releases/' in path:
            return copy.deepcopy(self.release)
        self.fail(f'Unexpected API: {path}')

    def gh(self, *args, **kwargs):
        self.commands.append(args)
        if args[0] == 'api':
            return json.dumps([[self.release] if self.release else []])
        if args[:2] == ('release', 'create'):
            self.release = {'id': 1, 'tag_name': 'v0.2.0', 'draft': True,
                            'assets': [], 'html_url': 'https://example.invalid/release'}
        elif args[:2] == ('release', 'upload'):
            asset = self.asset()
            if self.upload_bad_digest:
                asset['digest'] = 'sha256:wrong'
            self.release['assets'] = [asset]
        elif args[:2] == ('release', 'edit'):
            self.latest = args[-1]
            self.release['draft'] = False
        else:
            self.fail(f'Unexpected gh invocation: {args}')
        return ''

    def publish(self):
        publisher.publish('owner/repo', SHA, self.root)

    def test_upload_digest_checked_before_publication(self):
        self.publish()
        self.assertFalse(self.release['draft'])
        self.assertEqual(self.tag_sha, SHA)
        self.assertEqual(self.latest, '--latest=true')

    def test_bad_local_checksum_prevents_tag_or_upload(self):
        self.rpm.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            self.publish()
        self.assertIsNone(self.tag_sha)
        self.assertEqual(self.commands, [])

    def test_existing_tag_cannot_point_elsewhere(self):
        self.tag_sha = OTHER
        with self.assertRaises(ValueError):
            self.publish()
        self.assertIsNone(self.release)

    def test_bad_upload_stays_draft(self):
        self.upload_bad_digest = True
        with self.assertRaises(ValueError):
            self.publish()
        self.assertTrue(self.release['draft'])
        self.assertIsNone(self.latest)

    def test_retry_keeps_public_release_immutable(self):
        self.publish()
        self.commands.clear()
        self.publish()
        self.assertTrue(all(command[0] == 'api' for command in self.commands))

    def test_public_asset_mismatch_fails_without_overwrite(self):
        self.publish()
        self.release['assets'][0]['digest'] = 'sha256:wrong'
        self.commands.clear()
        with self.assertRaises(ValueError):
            self.publish()
        self.assertTrue(all(command[0] == 'api' for command in self.commands))

    def test_old_commit_does_not_replace_latest(self):
        self.main_sha = OTHER
        self.publish()
        self.assertEqual(self.latest, '--latest=false')

    def test_incomplete_draft_can_be_resumed(self):
        self.tag_sha = SHA
        self.gh('release', 'create')
        self.publish()
        self.assertFalse(self.release['draft'])


if __name__ == '__main__':
    unittest.main()
