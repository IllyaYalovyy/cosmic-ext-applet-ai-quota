# Changelog

## 0.1.2 — 2026-11-09

- Record standing authorization to push and publish verified changes.
- Publish the provider fixes and expanded tests from 0.1.1.

## 0.1.1 — 2026-11-08

- Honor the live refresh interval in both providers and rate-limit repeated popup refreshes.
- Back off after failed refreshes even while displaying retained cached data.
- Keep model-specific Codex quotas out of the overall meter when no main bucket exists.
- Check Claude cost envelopes on failed exits; kill and reap timed-out/oversized processes.
- Bound subprocess output to 1 MiB without adding dependencies or timers.
- Add offline provider/driver regressions and isolated release-policy tests to the quality gate.

## 0.1.0 — 2026-11-08

- First independent AI Quota release for the COSMIC panel and dock.
- Claude Code and Codex usage meters, reset windows, freshness and settings.
- Rename the binary, desktop entry, app ID and Codex client identity.
- Fedora 45 RPM with license notices and corresponding source included.
- Document migration from COSMIC Claudometer; enforce semantic version bumps.
- Keep original history in Claudometer; GNOME development returns there.
