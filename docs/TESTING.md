# Testing Strategy

This project values tests that protect user behavior and system invariants over
raw coverage percentages.

## Test Layers

Use the lowest layer that catches the risk clearly:

- **Unit tests** - pure functions, model invariants, parsing, validation,
  reducers, state transitions
- **Integration tests** - storage, API clients, process boundaries, migrations,
  serialization compatibility, concurrency contracts
- **UI / behavioral tests** - user flows, keyboard and pointer behavior,
  accessibility-visible state, layout regressions
- **Property / fuzz tests** - parsers, protocols, tree structures, state
  machines, and untrusted input
- **Manual checks** - hardware, external providers, stores, or other cases where
  automation is not practical

## Regression Rule

Every fixed bug should leave behind a test that fails without the fix.

Every new user-facing behavior should have a test that would fail if the behavior
disappeared.

## Applet coverage

- `src/claude.rs` tests cache parsing and the zero-cost refresh tripwire.
- `src/codex.rs` tests rate-limit parsing and fake App Server requests.
- `src/model.rs` tests panel and popup state derived from provider snapshots.
- `src/scheduler.rs` tests polling backoff.
- `src/window.rs` contains layout checks and the opt-in offscreen renderer.

Use a COSMIC session to verify panel placement, popup interaction, and live
settings changes.

## Local Quality Gate

Run:

```bash
./scripts/quality.sh
```

Add project-specific checks as executable files in `scripts/quality.d/`.

## Test Naming

Prefer names that describe the requirement:

```text
restores_workspace_after_process_restart
rejects_expired_token_without_overwriting_refresh_token
keeps_keyboard_focus_after_item_delete
```

Avoid names that only describe the implementation:

```text
test_update
manager_returns_true
component_renders
```

## Provider review regressions

All automatic tests use captured, sanitized data and offline fake executables;
they do not read personal provider credentials or start model turns.

- `source.rs`: 30-second and ten-minute intervals, repeated popup opens, live
  cadence changes, and manual refresh bypass through both providers.
- `claude.rs`: nonzero exit with model-cost evidence, zero-cost failures,
  permanent tripwire latch, cold-start give-up/manual recovery, output limits,
  timeouts, and process reaping.
- `codex.rs`: model-only quotas, request method allowlist, notifications,
  initialization responses, EOF/server/protocol errors, output limits and cleanup.
- `window.rs`: retained-data failure backoff, success recovery, stale generations,
  skipped ticks, and coalescing repeated manual requests.
- `tests/test_release_policy.py`: real isolated Git hooks, accepted version bumps,
  mismatched/staged metadata, author restrictions and inherited hook chaining.
  The quality gate runs these with standard-library unittest; pytest is not needed.

Run the optional renderer:

```sh
AI_QUOTA_RENDER_DIR=/tmp/ai-quota-review cargo test render_states -- --ignored
```

Inspect the generated PAM files, or convert them to PNG with ImageMagick.
This checks static layout, not live Wayland popup input or real provider-version
compatibility. Those still need a COSMIC session and signed-in clients; do not
treat fixture tests as proof that future CLI releases preserve their protocol
or token-free behavior.

## CI coverage

`.github/workflows/ci-release.yml` runs `scripts/ci-test.sh` for each selected
commit, covering both feature configurations, doc tests and the ignored visual
renderer. It also runs release-policy and CI planning/publication unit tests,
then builds and installs/removes the Fedora RPM. See packaging/README.md for
permissions, artifact retention, release gating, and rerun behavior.
