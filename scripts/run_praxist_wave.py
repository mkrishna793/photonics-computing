#!/usr/bin/env python3
"""Runner for PRAXIST Multi-Agent Research Generation Waves in Photonics Computing."""

import argparse
import json
import sys
from pathlib import Path

# Add project root and src to path
ws = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ws / "src"))

try:
    from prime_core import prime_db, prime_orchestrator, prime_repl
except ImportError:
    print("Error: prime_core not found.")
    sys.exit(1)


def plan_generation(topic: str, lanes: list[str]):
    print(f"\n🔍 Planning PRAXIST Generation for: '{topic}'")
    plan = prime_orchestrator.plan_praxist_cohort(query=topic, orthogonal_lanes=lanes)
    print(f"✓ Generation ID: {plan['generation_id']}")
    print(f"✓ Prior Negative Evidence to Avoid ({len(plan['negative_evidence_to_avoid'])} rules):")
    for rule in plan["negative_evidence_to_avoid"]:
        print(f"   {rule}")
    print("\nPlanned Cohort Facets:")
    for sub in plan["cohort"]:
        print(f"   • [{sub['lane_role']}] {sub['aspect']}")
    return plan


def record_finding(gen_id: int, aspect: str, mechanism: str, metrics: dict, caveats: str, lane: str, sources: list[str]):
    print(f"\n📝 Committing finding to lane [{lane.upper()}]...")
    prime_orchestrator.materialize_praxist_finding(
        generation_id=gen_id,
        aspect=aspect,
        mechanism=mechanism,
        metrics=metrics,
        caveats=caveats,
        lane=lane,
        sources=sources,
    )
    print("✓ Successfully materialized into PRAXIST evidence graph.")


def main():
    parser = argparse.ArgumentParser(description="PRAXIST Research Generation Wave Runner")
    parser.add_argument("--plan", action="store_true", help="Plan a new generation wave")
    parser.add_argument("--topic", type=str, default="Clements vs Reck MZI Mesh Scaling in Silicon Photonics", help="Research topic")
    parser.add_argument("--lanes", nargs="+", default=["Optical Loss & Depth Scaling", "Thermal Phase Drift & Tuning Power", "Error Tolerance & Quantization"], help="Orthogonal lanes")
    parser.add_argument("--status", action="store_true", help="Show current Frontier & Evidence Manifest")

    args = parser.parse_args()

    if args.status:
        frontier = prime_db.get_frontier_manifest()
        negatives = prime_db.get_negative_evidence_ledger()
        gems = prime_db.get_gems_ledger()
        print("\n" + "=" * 60)
        print("🏛️ PRAXIST Research Lineage Status")
        print(f"Frontier items: {len(frontier)} | Negative evidence items: {len(negatives)} | Gems: {len(gems)}")
        print("=" * 60)
        return

    if args.plan:
        plan_generation(args.topic, args.lanes)


if __name__ == "__main__":
    main()
