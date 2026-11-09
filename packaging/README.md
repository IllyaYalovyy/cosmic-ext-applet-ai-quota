# Fedora 45 RPM releases

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
RPM, not an official Fedora package or dist-git SRPM.

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

## GitHub Actions

The Test and release workflow runs on branch pushes, pull requests and manual
workflow dispatch. It enumerates each new first-parent commit in a push (up to
GitHub's 256-job matrix limit) and validates the actual PR head, not a synthetic
merge author's identity. Every commit must have its own semantic version bump
and Illya Yalovyy as its sole author. Force-push rewrites fail planning rather
than silently dropping commits. A newly created branch validates its tip.

Fedora 45 x86_64 build jobs run both renderer feature configurations, all unit,
integration and documentation tests, Clippy, formatting, the Python policy/CI
tests, and ignored offscreen render tests. They build the RPM and install,
verify and remove it inside the disposable container. Public releases wait
until every commit in the push passes. RPM/checksum artifacts are retained for
30 days and rendered PNGs for 14 days. Failed runs retain any render evidence
already produced. Dependency/build caches are keyed by Rust and Cargo.lock.

Only main pushes (or manual dispatch on main) can publish, using a separate job
with contents:write. Builds and PRs have read-only repository permission and no
provider secrets. Pinned official actions and a pinned Fedora container prevent
silent action/image changes. Version tags point to the tested commit, and the
RPM is verified against SHA256SUMS locally and GitHub's asset digest before the
draft is published. Reruns verify an already published release without replacing
its assets; a changed artifact or mismatched tag fails explicitly. An older
commit cannot mark itself latest after main has advanced. CI never creates a
Git commit, changes authors, or increments a version automatically.

Live COSMIC interactions and compatibility with signed-in provider clients
remain manual tests. The RPM remains unsigned. Rerun the original workflow to retry an older commit. workflow_dispatch runs
the selected branch tip, publishing only when main is selected; ordinary fix
commits trigger their own build/release.
