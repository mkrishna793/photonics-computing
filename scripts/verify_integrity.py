#!/usr/bin/env python3
"""Superpowers Anti-Early-Victory Verification Gate for Photonics Computing.

Executes full test suite and syntax verification, logging immutable records
to .prime-kernel/workspace.db.
"""

import subprocess
import sys
from pathlib import Path

ws = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ws / "src"))

try:
    from prime_core import prime_db, prime_orchestrator
except ImportError:
    print("Error: prime_core not found.")
    sys.exit(1)


def main():
    print("=" * 60)
    print("⚡ Superpowers Pre-Flight Code Integrity Gate")
    print("=" * 60)

    # 1. Run pytest
    print("\n[Gate 1/2] Running full pytest suite...")
    venv_pytest = ws / ".venv" / "bin" / "pytest"
    pytest_cmd = [str(venv_pytest) if venv_pytest.exists() else "pytest", "-v"]
    env = dict(PYTHONPATH="src")
    res_pytest = subprocess.run(pytest_cmd, cwd=ws, env=dict(subprocess.os.environ, **env), capture_output=True, text=True)

    if res_pytest.returncode != 0:
        print("❌ Test Suite FAILED!")
        print(res_pytest.stdout)
        print(res_pytest.stderr)
        prime_db.record_verification(
            target_type="test_suite",
            target_name="pytest_suite",
            status="failed",
            error_summary=res_pytest.stdout[-500:]
        )
        sys.exit(1)

    print("✓ All unit tests passed.")

    # 2. Syntax validation
    print("\n[Gate 2/2] Running AST syntax validation on src/ and tests/...")
    py_files = list((ws / "src").rglob("*.py")) + list((ws / "tests").rglob("*.py"))
    for py_file in py_files:
        with open(py_file, "r", encoding="utf-8") as f:
            code = f.read()
        try:
            compile(code, str(py_file), "exec")
        except SyntaxError as e:
            print(f"❌ Syntax error in {py_file}: {e}")
            prime_db.record_verification(
                target_type="source_file",
                target_name=str(py_file.relative_to(ws)),
                status="failed",
                error_summary=str(e)
            )
            sys.exit(1)

    print(f"✓ Validated syntax across {len(py_files)} Python source files.")

    # Record success
    prime_db.record_verification(
        target_type="suite",
        target_name="full_photonics_suite",
        status="passed",
        error_summary=""
    )
    print("\n🎉 All integrity gates PASSED! Verified zero regressions.\n")


if __name__ == "__main__":
    main()
