#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
repo=$(pwd)
for tool in cargo rustc python3 git tar gzip sha256sum rpmbuild rpmuncompress rpm readelf desktop-file-validate appstreamcli; do
    command -v "$tool" >/dev/null || { printf 'Missing build tool: %s\n' "$tool" >&2; exit 1; }
done
# Release assets must correspond to the committed source archive.
if [[ -n $(git status --porcelain --untracked-files=normal) ]]; then
    printf 'Commit the release changes before building artifacts.\n' >&2
    exit 1
fi
./scripts/check-version.py
./scripts/quality.sh
desktop-file-validate data/*.desktop
appstreamcli validate --no-net data/*.metainfo.xml
source /etc/os-release
if [[ $ID != fedora || $VERSION_ID != 45 ]]; then
    printf 'Build this release on Fedora 45.\n' >&2; exit 1
fi
version=$(python3 -c 'import tomllib; print(tomllib.load(open("Cargo.toml", "rb"))["package"]["version"])')
name=cosmic-ext-applet-ai-quota
appid=io.github.illyayalovyy.cosmic-ext-applet-ai-quota
host=$(rustc -vV | sed -n 's/^host: //p')
arch=$(rpm --eval '%{_target_cpu}')
case "$host" in
    x86_64-unknown-linux-gnu|aarch64-unknown-linux-gnu) ;;
    *) printf 'Unsupported release host: %s\n' "$host" >&2; exit 1 ;;
esac
export SOURCE_DATE_EPOCH
SOURCE_DATE_EPOCH=$(git show -s --format=%ct HEAD)
output="$repo/dist/$version"
mkdir -p "$repo/target"
work=$(mktemp -d "$repo/target/release-package.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$output" "$work/rpm/"{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS,tmp}
cargo build --release --locked --message-format=json > "$work/build.json"
cargo metadata --locked --format-version 1 --filter-platform "$host" > "$work/metadata.json"
package="$work/$name-$version"
mkdir -p "$package/usr/bin" "$package/usr/share/applications" "$package/usr/share/metainfo" "$package/usr/share/icons/hicolor/scalable/apps"
binary=$(python3 - "$work/build.json" "$name" <<'PYCODE'
import json, sys
paths = [entry['executable'] for line in open(sys.argv[1])
         if (entry := json.loads(line)).get('reason') == 'compiler-artifact'
         and entry['target']['name'] == sys.argv[2] and entry.get('executable')]
assert paths, 'Cargo did not report the applet executable'
print(paths[-1])
PYCODE
)
machine=$(LC_ALL=C readelf -h "$binary" | sed -n 's/.*Machine: *//p')
case "$arch:$machine" in
    'x86_64:Advanced Micro Devices X86-64'|'aarch64:AArch64') ;;
    *) printf 'Binary architecture does not match RPM target: %s:%s\n' "$arch" "$machine" >&2; exit 1 ;;
esac
install -m755 "$binary" "$package/usr/bin/$name"
install -m644 "data/$appid.desktop" "$package/usr/share/applications/"
install -m644 "data/$appid.metainfo.xml" "$package/usr/share/metainfo/"
install -m644 "data/icons/$appid-symbolic.svg" "$package/usr/share/icons/hicolor/scalable/apps/"
cp LICENSE README.md CHANGELOG.md "$package/"
license_expression=$(python3 scripts/bundle-dependencies.py "$work/metadata.json" "$work/dependency-sources" "$package/third-party-licenses")
git archive --format=tar HEAD | gzip -n > "$package/source.tar.gz"
tar --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner -C "$work" -czf "$package/dependency-sources.tar.gz" dependency-sources
cp packaging/README.md "$package/BUILDING.md"
rpm_configdir=${AI_QUOTA_RPM_CONFIGDIR:-$(rpm --eval '%{_rpmconfigdir}')}
"$rpm_configdir/elfdeps" --requires "$binary" | sort -u > "$work/elf-requires.txt"
if ! grep -q '^libc.so.6' "$work/elf-requires.txt"; then
    printf 'RPM ELF dependency scan returned no glibc requirement.\n' >&2
    exit 1
fi
python3 - "$version" "$license_expression" "$work/rpm/SPECS/ai-quota.spec" "$work/elf-requires.txt" <<'PY'
from pathlib import Path
import sys
text = Path('packaging/ai-quota.spec.in').read_text()
requires = '\n'.join('Requires: ' + line for line in Path(sys.argv[4]).read_text().splitlines())
Path(sys.argv[3]).write_text(text.replace('@VERSION@', sys.argv[1]).replace('@LICENSE@', sys.argv[2]).replace('@ELF_REQUIRES@', requires))
PY
tar --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner -C "$work" -czf "$work/rpm/SOURCES/$name-$version-payload.tar.gz" "$name-$version"
# AI_QUOTA_RPM_CONFIGDIR supports locally extracted build tools without a system install.
rpm_args=(--define "_topdir $work/rpm" --define "_tmppath $work/rpm/tmp"
          --define "__rpmuncompress $(command -v rpmuncompress)")
if [[ -n ${AI_QUOTA_RPM_CONFIGDIR:-} ]]; then rpm_args+=(--define "_rpmconfigdir $AI_QUOTA_RPM_CONFIGDIR"); fi
rpmbuild "${rpm_args[@]}" -bb "$work/rpm/SPECS/ai-quota.spec"
cp "$work/rpm/RPMS/$arch/"*.rpm "$output/"
(
    cd "$output"
    sha256sum ./*.rpm > SHA256SUMS
    sha256sum --check SHA256SUMS
)
printf 'Release RPM: %s\n' "$output"
