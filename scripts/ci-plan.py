#!/usr/bin/env python3
"""Select every mainline commit in a push; PRs validate their actual head."""
import json
import os
from pathlib import Path
import re
import subprocess


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def checked_sha(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{40}', value):
        raise ValueError('Expected a full commit SHA')
    return value


def commits_for_event(name, event, current):
    current = checked_sha(current)
    if name == 'pull_request':
        return [checked_sha(event['pull_request']['head']['sha'])]
    if name != 'push':
        return [current]
    before = checked_sha(event['before'])
    if before == '0' * 40:
        return [current]  # A new branch starts at its tip, not the whole history.
    subprocess.run(['git', 'merge-base', '--is-ancestor', before, current], check=True)
    commits = git('rev-list', '--first-parent', '--reverse', f'{before}..{current}').splitlines()
    if not commits or len(commits) > 256:
        raise ValueError('Push must contain 1–256 mainline commits')
    return commits


def main():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    commits = commits_for_event(os.environ['GITHUB_EVENT_NAME'], event, os.environ['GITHUB_SHA'])
    matrix = json.dumps({'sha': commits}, separators=(',', ':'))
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f'matrix={matrix}\n')
    print(matrix)


if __name__ == '__main__':
    main()
