#!/usr/bin/env python3
"""Persistent Prime Agent RLM REPL session connected to project workspace database."""

import sys
from pathlib import Path

# Add project root and src to path
ws = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ws / "src"))

try:
    from prime_core import prime_db, prime_repl
except ImportError:
    print("Error: prime_core not found. Ensure .venv or prime_env is active.")
    sys.exit(1)

def main():
    print("=" * 60)
    print("⚡ Prime Agent RLM Persistent REPL Session")
    print(f"📁 Workspace Database: {prime_db.get_db_path()}")
    print("=" * 60)

    # Boot kernel
    kernel = prime_repl.get_kernel()
    print("Ready. Type Python code to execute in persistent kernel. Type 'exit' to quit.\n")

    test_code = "import numpy as np; from photonics import OpticalTensorCore; core = OpticalTensorCore(4); print(f'Core initialized with {core.n} channels')"
    print(f"Executing pre-flight test:\n>>> {test_code}")
    res = prime_repl.run_code(test_code)
    print(res.get("output", ""))

if __name__ == "__main__":
    main()
