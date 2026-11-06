# src2/compare.py
"""
Day 5: put chunking strategies side by side.

Run from src2/:
    python compare.py
"""

import json
import statistics
from pathlib import Path

RESULTS = Path("../data/invoicepilot/results")
RUNS = {
    "seed": [("fixed-500", "baseline_v1"), ("recursive-500", "recursive_seed"),
             ("structure-aware", "structure_seed"), ("structure-ctx", "ctx_seed")],
    "hard": [("fixed-500", "baseline_v1_hard"), ("recursive-500", "recursive_hard"),
             ("structure-aware", "structure_hard"), ("structure-ctx", "ctx_hard")],
}

for set_name, runs in RUNS.items():
    print(f"\n=== {set_name} set ===")
    print(f"{'strategy':16s} {'r@1':>5s} {'r@5':>5s} {'MRR':>5s} {'avg margin':>11s} {'neg':>4s} "
          f"{'correct':>8s} {'tokens in':>10s}")
    for label, run in runs:
        data = json.loads((RESULTS / f"{run}.json").read_text())
        s, rows = data["summary"]["ALL"], data["rows"]
        margins = [r["margin"] for r in rows if r["margin"] is not None]
        neg = sum(m < 0 for m in margins)
        tokens = statistics.mean(r["tokens_in"] for r in rows)
        print(f"{label:16s} {s['recall@1']:>5.0%} {s['recall@5']:>5.0%} {s['mrr']:>5.2f} "
              f"{statistics.mean(margins):>+11.3f} {neg:>4d} {s['correct']:>8.0%} {tokens:>10.0f}")

    # which questions changed rank between fixed and structure-aware?
    base = {r["id"]: r for r in json.loads((RESULTS / f"{runs[2][1]}.json").read_text())["rows"]}
    new = {r["id"]: r for r in json.loads((RESULTS / f"{runs[3][1]}.json").read_text())["rows"]}
    changed = [(i, base[i]["first_hit_rank"], new[i]["first_hit_rank"]) for i in base
               if base[i]["first_hit_rank"] != new[i]["first_hit_rank"]]
    print("rank changes, fixed -> structure-aware:", changed or "none")