# RFC-008: Display verified provider metadata compactly

Status: Implemented
Author: Illya Yalovyy

## Evidence and goals
A live, read-only check with Codex CLI 0.166.0 and Claude Code 2.1.330
on 2026-11-21 confirmed both quota protocols. Claude /usage reported zero
cost, zero model tokens and an empty modelUsage object. The app ignores useful
metadata already returned with the same requests.

Add Claude's weekly surface breakdown, scoped weekly allowance share and extra
usage state; add Codex's plan, credit balance, spend-control state and earliest
available reset-credit expiry. Do not expose account or credit IDs, promotional
copy, or interactive purchase/reset controls. Do not parse Claude's prose usage
suggestions: those are overlapping local-session estimates, not account quotas.

## Options and decision
Adding a bar for each field duplicates existing quotas and increases height.
Instead, put compact caption details under the existing groups and model rows.
Breakdown percentages are explicitly shares of weekly usage; scoped share values
are percentages of the weekly allowance, not the model's separate usage bar.
Hide zero-contribution breakdown entries, unknown optional fields, and absent
expiry values. Preserve the existing quota bars if optional metadata is malformed.
Keep credit units as credits; no currency is inferred for Codex balances.

## Validation and rollout
Use sanitized structural fixtures with synthetic quota values and timestamps,
no account/credit IDs. Test valid, absent, malformed and expired metadata,
shared-window indices and unchanged quota selection. Assert the complete enriched
normal and multi-model popup fits a 720 px content area without scrolling; retain
small-viewport fallback tests and inspect offscreen renders. Run both feature
configurations and CI packaging. Bump minor version for new displayed fields.

## Development plan
- [x] Add typed optional parser metadata and sanitized fixtures.
- [x] Add compact display details and parser/model/layout regressions.
- [x] Validate live captures through the updated parsers, both feature configurations and renders.

Release rollout: push version 0.3.0 and observe CI through RPM publication and
checksum verification. Refresh results are boxed to keep UI messages compact.
