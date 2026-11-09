//! Provider reads are independent and concurrent. An unavailable provider
//! never hides a healthy snapshot from the other provider.

use std::sync::Arc;
use std::sync::atomic::AtomicBool;

use crate::claude::{ClaudeConfig, ClaudeSnapshot, ClaudeSource};
use crate::codex::{CodexConfig, CodexSnapshot, CodexSource};

/// Bound subprocess output independently of its timeout.
pub(crate) const MAX_PROVIDER_OUTPUT_BYTES: u64 = 1024 * 1024;

/// The combined snapshot the render models consume.
#[derive(Debug, Clone, PartialEq)]
pub struct Snapshot {
    pub claude: ClaudeSnapshot,
    pub codex: CodexSnapshot,
}

/// Whether the most recent refresh of each provider actually failed (#16).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct RefreshFailed {
    pub claude: bool,
    pub codex: bool,
}

/// Everything one fetch cycle hands back to the UI thread.
#[derive(Debug, Clone, PartialEq)]
pub struct FetchOutput {
    pub snapshot: Snapshot,
    pub last_refresh_failed: RefreshFailed,
    /// Current value of the G1 tripwire latch, so the applet can persist a
    /// trip that happened during this fetch.
    pub claude_refresh_disabled: bool,
}

pub struct MultiSource {
    claude: ClaudeSource,
    codex: CodexSource,
}

impl MultiSource {
    pub fn new(refresh_disabled: Arc<AtomicBool>) -> Self {
        Self {
            claude: ClaudeSource::new(ClaudeConfig::default(), refresh_disabled),
            codex: CodexSource::new(CodexConfig::default()),
        }
    }

    pub async fn fetch(&mut self, now: i64, manual: bool, interval_seconds: u32) -> FetchOutput {
        let refresh_after_ms = i64::from(interval_seconds) * 1000;
        let (claude, codex) = tokio::join!(
            self.claude.fetch(now, manual, refresh_after_ms),
            self.codex.fetch(now, manual, refresh_after_ms)
        );
        FetchOutput {
            snapshot: Snapshot { claude, codex },
            last_refresh_failed: RefreshFailed {
                claude: self.claude.last_refresh_failed(),
                codex: self.codex.last_refresh_failed(),
            },
            claude_refresh_disabled: self.claude.refresh_disabled(),
        }
    }
}

impl Snapshot {
    /// Whether either provider's fetch produced an error snapshot — the
    /// scheduler's backoff trigger.
    pub fn has_error(&self) -> bool {
        self.claude.is_error() || self.codex.is_error()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::{TestDir, fake_cli};
    use std::time::Duration;

    #[tokio::test]
    async fn selected_interval_reaches_both_providers_and_limits_repeated_opens() {
        let dir = TestDir::new();
        let claude_pid = dir.join("claude-pid");
        let codex_pid = dir.join("codex-pid");
        let cache = dir.join("claude.json");
        let data: serde_json::Value = serde_json::from_str(include_str!(
            "../tests/fixtures/cached-usage-utilization.json"
        ))
        .unwrap();
        let now = data["fetchedAtMs"].as_i64().unwrap();
        std::fs::write(
            &cache,
            serde_json::json!({"cachedUsageUtilization": data}).to_string(),
        )
        .unwrap();
        let mut source = MultiSource {
            claude: ClaudeSource::new(
                ClaudeConfig {
                    file_path: cache,
                    refresh_argv: fake_cli("ok", &claude_pid),
                    refresh_timeout: Duration::from_secs(5),
                },
                Arc::new(AtomicBool::new(false)),
            ),
            codex: CodexSource::new(CodexConfig {
                app_server_argv: fake_cli("codex-quota", &codex_pid),
                timeout: Duration::from_secs(5),
            }),
        };
        assert!(!source.fetch(now, false, 30).await.snapshot.has_error());
        assert!(!claude_pid.exists()); // fresh file needs no CLI
        std::fs::remove_file(&codex_pid).unwrap();
        source.fetch(now + 30_000, false, 30).await;
        assert!(claude_pid.exists() && codex_pid.exists()); // 30s, not hard-coded 60s
        std::fs::remove_file(&claude_pid).unwrap();
        std::fs::remove_file(&codex_pid).unwrap();
        source.fetch(now + 46_000, false, 30).await; // popup opens after 16s
        assert!(!claude_pid.exists() && !codex_pid.exists());
        source.fetch(now + 90_000, false, 600).await; // live change to ten minutes
        assert!(!claude_pid.exists() && !codex_pid.exists());
        source.fetch(now + 630_000, false, 600).await;
        assert!(claude_pid.exists() && codex_pid.exists());
        std::fs::remove_file(&claude_pid).unwrap();
        std::fs::remove_file(&codex_pid).unwrap();
        source.fetch(now + 630_001, true, 600).await; // explicit manual bypass
        assert!(claude_pid.exists() && codex_pid.exists());
    }
}
