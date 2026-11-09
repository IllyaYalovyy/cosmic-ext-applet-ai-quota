#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
python3 scripts/ci-check-commit.py
./scripts/quality.sh
cargo test --locked --doc --all-features
cargo clippy --locked --all-targets --no-default-features -- -D warnings
cargo test --locked --all-targets --no-default-features
cargo test --locked --doc --no-default-features
for mode in gpu software; do
    flags=(--all-features)
    if [[ $mode == software ]]; then flags=(--no-default-features); fi
    output="$PWD/target/ci-evidence/$mode"
    mkdir -p "$output"
    AI_QUOTA_RENDER_DIR="$output" cargo test --locked --all-targets "${flags[@]}" -- --ignored
    for frame in "$output"/*.pam; do
        magick "$frame" "${frame%.pam}.png"
    done
done
desktop-file-validate data/*.desktop
appstreamcli validate --no-net data/*.metainfo.xml
