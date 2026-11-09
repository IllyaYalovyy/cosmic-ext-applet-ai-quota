#!/usr/bin/env python3
"""Check release metadata; --staged requires a semantic bump over HEAD."""
from pathlib import Path
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent.parent
staged = '--staged' in sys.argv
committed = '--commit' in sys.argv


def git(*args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True)


def read(path):
    if staged or committed:
        return git('show', (':' if staged else 'HEAD:') + path)
    return (root / path).read_text()


def version_tuple(value):
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value):
        sys.exit('Version must be major.minor.patch without leading zeroes')
    return tuple(map(int, value.split('.')))


manifest = tomllib.loads(read('Cargo.toml'))['package']
version = manifest['version']
new = version_tuple(version)
lock = tomllib.loads(read('Cargo.lock'))
package = next(p for p in lock['package'] if p['name'] == manifest['name'])
if package['version'] != version:
    sys.exit('Cargo.lock version differs')
release = ET.fromstring(read('data/io.github.illyayalovyy.cosmic-ext-applet-ai-quota.metainfo.xml')).find('releases/release')
if release is None or release.attrib['version'] != version:
    sys.exit('AppStream version differs')
heading = next(line for line in read('CHANGELOG.md').splitlines() if line.startswith('## '))
if not heading.startswith(f'## {version} '):
    sys.exit('Changelog version differs')
if staged or committed:
    base = 'HEAD' if staged else 'HEAD^'
    has_head = subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', base], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    previous = tomllib.loads(git('show', base + ':Cargo.toml'))['package'] if has_head else None
    if previous is not None:
        old = version_tuple(previous['version'])
        allowed = ((old[0] + 1, 0, 0), (old[0], old[1] + 1, 0), (old[0], old[1], old[2] + 1))
        if new not in allowed:
            sys.exit('Every changeset needs one major, minor, or patch bump over HEAD')
print(f'Release metadata agrees: {version}')
