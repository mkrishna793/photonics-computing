#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/audit_repository.py
cargo test --locked --offline --manifest-path Lean-Semantics/rust/Cargo.toml
cargo build --locked --offline --manifest-path Lean-Semantics/rust/Cargo.toml
python3 -m unittest discover -s tests -v
