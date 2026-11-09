//! Isolated test files; no provider clients or user configuration are accessed.
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

pub struct TestDir(PathBuf);

impl TestDir {
    pub fn new() -> Self {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "ai-quota-test-{}-{stamp}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }

    pub fn join(&self, name: &str) -> PathBuf {
        self.0.join(name)
    }
}

impl Drop for TestDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

pub fn fake_cli(mode: &str, record: &Path) -> Vec<String> {
    vec![
        concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/tests/fixtures/bin/provider-cli"
        )
        .into(),
        mode.into(),
        record.display().to_string(),
    ]
}

pub fn assert_reaped(record: &Path) {
    let pid = std::fs::read_to_string(record).expect("fake CLI must start before the timeout");
    assert!(
        !Path::new(&format!("/proc/{}", pid.trim())).exists(),
        "child {pid} was not reaped"
    );
}
