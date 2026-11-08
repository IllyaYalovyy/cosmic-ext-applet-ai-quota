# Manual Fedora 45 RPM releases

Build on Fedora 45 with Rust stable, cargo, gcc, pkgconf-pkg-config,
libxkbcommon-devel, wayland-devel, rpm-build, rpm, binutils, python3, git,
tar, gzip, desktop-file-utils and appstream installed. The locked libcosmic dependencies require a current
stable Rust compiler.

```sh
./scripts/install-git-hooks.sh
./scripts/quality.sh
# Commit the release version and changelog first.
./scripts/build-release.sh
```

The script requires a clean committed tree and builds the locked release
executable, validates architecture, scans ELF library requirements, and packages
the applet and licenses. Output is under dist/<version>/. Only the RPM is
uploaded; SHA256SUMS is a local verification aid. This is an upstream binary
RPM, not an official Fedora package or dist-git SRPM. No CI/CD is configured.

The RPM includes source.tar.gz (the exact application source and build scripts)
and dependency-sources.tar.gz (exact Cargo dependency source trees and their
provenance inventory), plus license notices under /usr/share/licenses. These
archives account for much of the RPM size. They are source archives, not an
automatically configured Cargo vendor directory. To rebuild normally, extract
source.tar.gz, install the tools above, then run cargo build --release --locked;
Cargo fetches the pinned dependencies. The bundled dependency inventory records
each source tree and upstream source ID for reconstruction without relying on
upstream retention.

AI_QUOTA_RPM_CONFIGDIR can point to locally extracted RPM build tools; the
matching rpmbuild and rpmuncompress must also be on PATH.
