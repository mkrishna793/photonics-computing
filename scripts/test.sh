#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export PYTHONPATH="src:scripts:${PYTHONPATH:-}"

python3 scripts/audit_repository.py
cargo test --locked --offline --manifest-path Lean-Semantics/rust/Cargo.toml
cargo build --locked --offline --manifest-path Lean-Semantics/rust/Cargo.toml

# If pytest and scientific dependencies are available, run the full 50-test suite
if python3 -c "import pytest, numpy" 2>/dev/null; then
    echo "Running full test suite via pytest..."
    python3 -m pytest -v
else
    echo "Running base pipeline test suite via unittest (pure standard library)..."
    python3 -m unittest discover -s tests -p "test_pipeline.py" -v
fi
