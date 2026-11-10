#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v lake >/dev/null || { echo 'Lean/Lake unavailable. Install elan and the pinned toolchain.' >&2; exit 1; }
bundle="$(realpath "${1:-artifacts/mzi-demo}")"
python3 scripts/check_certificate.py "$bundle" --lean "$bundle/Certificate.lean"
cd Lean-Semantics/lean
lake build
lake env lean "$bundle/Certificate.lean"
echo 'Lean library and generated numeric obligations checked. See docs/verification.md for remaining trust assumptions.'
