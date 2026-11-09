# RFC-005: Provider correctness and regression coverage

Status: Implemented
Author: Illya Yalovyy

## Problem and goals
Review found that provider cadence stays at 60 seconds despite live settings,
retained cached data hides refresh failures from backoff, model-only Codex
buckets can become the overall meter, and nonzero Claude exits bypass the
model-cost tripwire. Subprocess output also has no memory bound. Existing tests
mostly exercise parsing; driver transitions and release guards need regression
coverage.

## Options and decision
Reporting findings alone leaves confirmed failures in the next release. Choose
small fixes within the existing provider/driver modules, with offline fake CLI
and pure-state tests. Avoid replacing the scheduler or introducing dependencies.
No real provider processes, model calls, credentials, or CI/CD are needed.

## Design
Pass the selected refresh interval into every provider fetch. Keep manual
refresh semantics and a single in-flight fetch. Back off on refresh failures
even when a last-good snapshot is returned. Do not select an arbitrary named
Codex model as the main bucket; keep its detailed windows available.
Inspect a Claude cost envelope even on nonzero exit and preserve the tripwire.
Cap each subprocess response at 1 MiB; kill/reap on timeout or oversized output.

## Validation
First demonstrate failures against existing code. Cover 30/60/600-second
cadence, retained-data failures, model-only buckets, failed cost envelopes,
malformed/oversized/timeout subprocess output, request allowlisting, and queued
manual refreshes. Add durable isolated tests for semantic version and author
hooks. Run formatting, Clippy, all Rust and Python tests, metadata checks and
the opt-in offscreen renderer. Live compositor/provider testing remains manual.

## Development plan
- [x] Reproduce the confirmed provider/driver defects with tests.
- [x] Fix them without changing storage schema or adding dependencies.
- [x] Add release-policy tests to the local quality gate.
- [x] Run the complete gate and visual smoke test; record limitations.

## Compatibility and rollout
Patch bump to 0.1.1: these restore documented behavior. Keep schema v1 and the
existing app ID. No release or remote push is needed for this code review;
leave a reviewed local commit. Rollback is a normal revert with a version bump.

## Validation results

The old behavior fails focused regressions for the nonzero-exit tripwire,
model-only quota selection and retained-data backoff. The fixes pass 48 Rust
unit/integration tests and 8 isolated release-policy tests, plus formatting,
Clippy, the software-renderer build check (`--no-default-features`),
desktop/AppStream validation and the optional renderer (13 states).
The rendered normal, settings, degraded, stale/denied and empty popups were
visually inspected. Live Wayland interactions and real signed-in provider
compatibility were not exercised. No runtime dependencies or timers were added.
