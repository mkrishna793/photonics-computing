#!/usr/bin/env python3
"""Check project wiring without pretending to compile Lean proofs."""

import json
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]
LEAN = ROOT / "Lean-Semantics/lean"
config = tomllib.loads((LEAN / "lakefile.toml").read_text())
manifest = json.loads((LEAN / "lake-manifest.json").read_text())
assert config["require"][0]["rev"] == manifest["packages"][0]["inputRev"]
assert (LEAN / "lean-toolchain").read_text().strip().endswith(config["require"][0]["rev"])
files = {
    str(p.relative_to(LEAN)).removesuffix(".lean").replace("/", "."): p
    for p in LEAN.rglob("*.lean")
    if ".lake" not in p.parts
}
graph = {}
for module, path in files.items():
    source = path.read_text()
    # Match declarations, not words in doc comments.
    assert not re.search(r"(?m)^\s*(?:axiom\s|.*:=\s*(?:sorry|admit)\s*$)", source), path
    graph[module] = re.findall(r"(?m)^import (Lumiris(?:\.[A-Za-z0-9_]+)*)\s*$", source)
    for imported in graph[module]:
        assert imported in files, f"missing module {imported} imported by {path}"
seen, active = set(), set()


def visit(module):
    assert module not in active, f"import cycle: {module}"
    if module in seen:
        return
    active.add(module)
    for imported in graph[module]:
        visit(imported)
    active.remove(module)
    seen.add(module)


visit("Lumiris")
assert seen == set(files), f"unbuilt Lean modules: {set(files)-seen}"
rust = ROOT / "Lean-Semantics/rust"
cargo = tomllib.loads((rust / "Cargo.toml").read_text())
assert (rust / cargo["lib"]["path"]).is_file()
for binary in cargo["bin"]:
    assert (rust / binary["path"]).is_file()
print(
    f"PASS: {len(files)} Lean modules reachable, imports resolved, pins aligned, Rust targets exist. This is a layout audit, not proof validation."
)
