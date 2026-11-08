# RFC-004: Separate AI Quota and GNOME Claudometer

Status: Implemented
Author: Illya Yalovyy

## Problem and goals
Give the COSMIC usage applet its own public identity, repository and Fedora 45
RPM, while restoring the GNOME extension on Claudometer main. Preserve original history in Claudometer
and preserve provider behavior. Do not add CI/CD or new runtime dependencies.

## Options and decision
Sharing history would retain older co-author trailers. Choose a clean import
authored solely by Illya Yalovyy; original history stays in Claudometer. Restore the old
repository tree from its gnome-extension branch with a normal forward commit;
never force-push main. Historical commits remain unchanged.

## Design and user impact
Name the app AI Quota, package cosmic-ext-applet-ai-quota and application ID
io.github.illyayalovyy.cosmic-ext-applet-ai-quota. Start its independent release
line at 0.1.0. Document migration of old COSMIC settings, including the safety
tripwire. GNOME retains its existing extension UUID and settings schema.
Build manually on Fedora 45. Publish only the binary RPM; include corresponding
application and dependency sources and license notices inside the RPM so it is
self-contained. Preserve source MIT licensing and dependency license terms.
Require a major/minor/patch version change for every subsequent changeset,
with Cargo, AppStream and changelog versions checked by the quality gate.

## Verification and rollout
Run Rust formatting, clippy and unit tests; validate desktop/AppStream files,
RPM dependencies and payload, and uploaded artifact digest. Run the restored
GNOME quality gate. Inspect author identity and staged diffs before committing.
Create and publish the new repository before updating Claudometer main. A
normal revert can undo the GNOME restoration without rewriting history.

## Development plan
- [x] Rename app and document migration and version policy.
- [x] Provide a manual Fedora 45 RPM build and validation script.
- [x] Create the separate public repository with sole-author import policy.
- [x] Restore and test the GNOME tree in the original repository.

Release execution follows the validation and rollout procedure above; its
results are recorded in the GitHub release notes.

No unresolved design questions. Provider code changes are mechanical naming
changes only; existing provider tests cover their behavior.
