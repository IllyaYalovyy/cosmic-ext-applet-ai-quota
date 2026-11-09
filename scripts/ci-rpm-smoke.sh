#!/usr/bin/env bash
# Run only in the disposable Fedora CI container: installs/removes the package.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
version=$(python3 -c 'import tomllib; print(tomllib.load(open("Cargo.toml", "rb"))["package"]["version"])')
name=cosmic-ext-applet-ai-quota
rpm_file="$PWD/dist/$version/$name-$version-1.fc45.x86_64.rpm"
(cd "dist/$version" && sha256sum --check SHA256SUMS)
# Minimal Fedora images default to tsflags=nodocs; verify the full payload.
dnf -y --setopt=tsflags= install "$rpm_file"
rpm -V "$name"
ldd "/usr/bin/$name" | tee "$RUNNER_TEMP/ai-quota-ldd.txt"
if grep -q 'not found' "$RUNNER_TEMP/ai-quota-ldd.txt"; then exit 1; fi
python3 - "$name" "$version" <<'PY'
from pathlib import Path
import subprocess
import sys
import tarfile
name, version = sys.argv[1:]
# Fedora macro sets may use either a versioned or unversioned doc directory.
files = subprocess.check_output(['rpm', '-ql', name], text=True).splitlines()
source = next(p for p in files if p.endswith('/source.tar.gz'))
with tarfile.open(source) as archive:
    expected = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    assert archive.pax_headers['comment'] == expected
    assert archive.extractfile('Cargo.toml').read() == Path('Cargo.toml').read_bytes()
assert any(p.endswith('/dependency-sources.tar.gz') for p in files)
PY
dnf -y remove "$name"
if rpm -q "$name"; then exit 1; fi
test ! -e "/usr/bin/$name"
