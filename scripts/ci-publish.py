#!/usr/bin/env python3
"""Publish only the tested commit's RPM; never overwrite a public artifact."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parent.parent


def gh(*args, input_text=None, missing=False):
    result = subprocess.run(['gh', *args], input=input_text, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        if missing and 'HTTP 404' in result.stderr:
            return None
        raise RuntimeError(result.stderr)
    return result.stdout


def api(path, payload=None, missing=False, method="POST"):
    args = ['api', path]
    if payload is not None:
        args += ['--method', method, '--input', '-']
    output = gh(*args, input_text=json.dumps(payload) if payload is not None else None,
                missing=missing)
    return json.loads(output) if output is not None else None


def artifact(directory, version):
    files = list(Path(directory).rglob('*.rpm'))
    if len(files) != 1:
        raise ValueError('Expected exactly one RPM')
    path = files[0]
    expected = f'cosmic-ext-applet-ai-quota-{version}-1.fc45.x86_64.rpm'
    if path.name != expected:
        raise ValueError('RPM does not match the checked-out version and target')
    rows = (path.parent / 'SHA256SUMS').read_text().splitlines()
    if len(rows) != 1:
        raise ValueError('Expected one checksum')
    digest, name = rows[0].split()
    if name.removeprefix('./') != expected:
        raise ValueError('Checksum filename does not match RPM')
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != actual:
        raise ValueError('RPM checksum mismatch')
    return path, actual


def verify_asset(release, path, digest):
    assets = release['assets']
    if len(assets) != 1:
        raise ValueError('Release must contain exactly one RPM asset')
    item = assets[0]
    if (item['name'], item['size'], item['digest'], item['state']) != (
            path.name, path.stat().st_size, 'sha256:' + digest, 'uploaded'):
        raise ValueError('GitHub asset does not match the tested RPM')


def find_release(repo, tag):
    pages = json.loads(gh('api', f'repos/{repo}/releases?per_page=100', '--paginate', '--slurp'))
    return next((release for page in pages for release in page if release['tag_name'] == tag), None)


def publish(repo, sha, directory):
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo) or not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Invalid repository or commit')
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if sha != actual:
        raise ValueError('Publication SHA must match the tested checkout')
    version = tomllib.loads((ROOT / 'Cargo.toml').read_text())['package']['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Expected semantic version')
    path, digest = artifact(directory, version)
    tag = 'v' + version
    reference = api(f'repos/{repo}/git/ref/tags/{tag}', missing=True)
    if reference is None:
        api(f'repos/{repo}/git/refs', {'ref': 'refs/tags/' + tag, 'sha': sha})
    if api(f'repos/{repo}/commits/{tag}')['sha'] != sha:
        raise ValueError('Release tag points to another commit; refusing to publish')
    release = find_release(repo, tag)
    if release is not None and not release['draft']:
        verify_asset(release, path, digest)
        print('Existing public release verified; unchanged:', release['html_url'])
        return
    if release is None:
        changelog = (ROOT / 'CHANGELOG.md').read_text().split('\n## ', 2)[1]
        notes = (f'Automated Fedora 45 x86_64 release for commit `{sha}`.\n\n'
                 + changelog.split('\n', 1)[1]
                 + '\n\nAll offline tests, both renderer configurations, offscreen renders, '
                 'and RPM install/remove checks passed. Live COSMIC/provider-account checks remain manual.\n'
                 '\nThe unsigned RPM includes corresponding source and license notices.\n'
                 f'\nSHA-256: `{digest}`\n')
        release = api(f'repos/{repo}/releases', {
            'tag_name': tag, 'name': f'AI Quota {version}', 'body': notes,
            'draft': True, 'target_commitish': sha,
        })
    # Use the returned ID: GitHub release listings can lag behind creation.
    release_id = release['id']
    if not release['assets']:
        gh('api', f'https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={path.name}',
           '--method', 'POST', '--header', 'Content-Type: application/x-rpm',
           '--input', str(path))
    release = api(f'repos/{repo}/releases/{release_id}')
    verify_asset(release, path, digest)
    current_main = api(f'repos/{repo}/commits/main')['sha']
    published = api(f'repos/{repo}/releases/{release_id}', {
        'draft': False, 'make_latest': 'true' if current_main == sha else 'false',
    }, method='PATCH')
    if published['draft']:
        raise ValueError('Release remained a draft')
    verify_asset(published, path, digest)
    print('Published and verified:', published['html_url'])


if __name__ == '__main__':
    publish(os.environ['GITHUB_REPOSITORY'], os.environ['RELEASE_SHA'], sys.argv[1])
