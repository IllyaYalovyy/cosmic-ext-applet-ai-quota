# RFC-006: Test and publish every main commit

Status: Accepted
Author: Illya Yalovyy

## Goals
Automate the existing Fedora 45 release process and all tests that can run
without real provider credentials or a desktop session. Publish every new
first-parent commit on main, including multi-commit pushes. Preserve sole-author
commits and explicit semantic version bumps; CI must never create commits.

## Options and decision
A workflow that builds only the push tip would skip intermediate main commits.
Choose a planning job that enumerates main commits, then a build matrix and a
separate publishing matrix. Pull requests validate their proposed head without
publishing. Manual dispatch retries the selected revision. Use Fedora 45 x86_64
in a pinned container, and pin official actions to immutable commits.

## Design
Read-only jobs run formatting, both feature configurations with Clippy/unit/
integration/doc tests, all ignored offscreen render tests, Python release-policy
tests, version/author validation, desktop metadata validation and a real RPM
install/remove smoke test. Preserve rendered evidence and the RPM/checksums as
workflow artifacts. Cache dependencies/build outputs with toolchain/lock keys.
Only the publish job receives contents:write; it runs only for main pushes or
manual main dispatch after all build jobs succeed. It verifies downloaded
checksums, binds the version tag to the tested SHA, uploads a draft release,
verifies GitHub's asset digest and then publishes. Existing public assets are
immutable; a mismatch fails rather than replacing them. Older commits never
replace a newer release as latest. Do not cancel earlier push runs.

## Scope and limitations
Branch pushes and PRs get validation artifacts; public releases come from main.
Live COSMIC pointer/window interactions and signed-in providers remain manual.
No accounts, model calls, self-hosted runners, new runtime dependencies or
automatic version/author commits. The existing unsigned RPM format is retained.

## Validation and rollout
Add isolated planning/publishing tests with mocked GitHub commands, validate
workflow syntax with actionlint, run the local quality gate, push, and observe
an actual GitHub Actions run through a published RPM with matching checksum.
Retrying an existing public release verifies its tag/digest and leaves it intact.

## Development plan
- [x] Add CI planning, commit checks and publication helpers with tests.
- [x] Add the Fedora test/build and isolated publish workflow.
- [x] Update release policy/docs and bump minor version to 0.2.0.
- [x] Validate workflow syntax, both local feature configurations and Fedora bootstrap.

Rollout: observe the first hosted run through publication; its Actions log and
release asset digest provide the end-to-end validation record.
