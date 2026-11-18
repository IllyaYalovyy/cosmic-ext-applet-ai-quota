# RFC-007: Compact, content-sized quota popup

Status: Implemented
Author: Illya Yalovyy

## Problem and goals
The 500 px body cap creates scrolling on ordinary desktops. Limit warnings
repeat each quota's percentage and reset time, while Codex labels use an extra
line for the duration. Keep all quota data readable without that duplication.

## Options and decision
Increasing the body cap alone keeps unnecessary rows and can clip the footer
on small surfaces. Instead, use compact quota rows and a single shrink-sized
scroll container for the complete popup. It grows with content up to the
standard COSMIC 1000 px popup limit. Compositor-constrained surfaces may scroll;
the footer remains reachable inside the same scrollable content.

Use a 360 px preferred width, COSMIC's standard popup width. Combine bucket and
duration labels, keep percentages beside labels and reset text below, and tighten
vertical spacing. Remove top limit promotions. Preserve distinct access/workspace
failure explanations and earned-reset counts as provider notes; percentages,
bar colors and reset times remain on their existing quota rows. Long labels wrap
without truncation. Enable Wayland resize constraints for small
outputs. No polling, protocol, dependencies or persistence changes.

## Validation and rollout
Assert the complete normal and limit-hit fixture fits without overflow, and that
a small surface scrolls with every quota and footer still in its content. Render
normal, limit-hit, degraded and constrained states with both feature sets.
Run the quality gate and existing CI/release workflow. Actual compositor input
and monitor placement require a live COSMIC session and are reported separately.

## Development plan
- [x] Remove duplicate promotion data and preserve distinct provider notices.
- [x] Compact quota rows and allow content-sized scrolling fallback.
- [x] Add layout regressions and review render evidence.
- [x] Prepare patch version 0.2.4 and pass both local feature configurations.

Release rollout: push and observe CI through publication and checksum verification.
