#!/usr/bin/env python3
"""Validate the tested commit, never the synthetic PR merge identity."""
import re
import subprocess

raw = subprocess.check_output(['git', 'log', '-1', '--format=%an%x00%ae%x00%B'], text=True)
name, email, message = raw.split('\0', 2)
if (name, email) != ('Illya Yalovyy', '1623643+IllyaYalovyy@users.noreply.github.com'):
    raise SystemExit('Commit must have Illya Yalovyy as its sole author')
if re.search(r'^\s*Co-authored-by\s*:', message, re.I | re.M):
    raise SystemExit('Co-authored-by trailers are forbidden')
subprocess.run(['python3', 'scripts/check-version.py', '--commit'], check=True)
