#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
out="${1:-artifacts/mzi-demo}"
cargo run --locked --offline --manifest-path Lean-Semantics/rust/Cargo.toml -- \
  compile examples/mzi-scale.lumi "$out" --device devices/demo-mzi.mzi
python3 scripts/check_certificate.py "$out" --source examples/mzi-scale.lumi \
  --device devices/demo-mzi.mzi --lean "$out/Certificate.lean" --report "$out/verification.json"
python3 scripts/simulate.py "$out" --report "$out/simulation.json"
if [[ "${2:-}" == "--lean" ]]; then
  scripts/check_lean.sh "$out"
else
  printf '\nLean was not executed. To check the formal library and generated numeric obligations:\n  scripts/check_lean.sh %q\n' "$out"
fi
