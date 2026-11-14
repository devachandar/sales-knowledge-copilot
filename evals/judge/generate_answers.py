# evals/judge/generate_answers.py
"""
Day 10, step 1: pick the 25 cases to hand-label and generate the system's answers for them.

The 25 are a fixed, stratified sample of the DEV split (never test): a few from every slice,
including slices where the system is expected to fail (refusals, injection, conflict), so both
pass and fail labels appear. The chosen ids are saved, so the same 25 are reused every time
the judge is re-run.

Run from the project root:
    python -m evals.judge.generate_answers
Writes:
    evals/judge/label_set.json                         the 25 ids (written once, then reused)
    data/invoicepilot/results/judge_answers.json       the answers + everything a labeler needs
"""

import json
import random
from collections import defaultdict
from pathlib import Path

from copilot.config import RESULTS_DIR
from copilot.generation.answer_v4 import answer
from copilot.retrieval.pipeline import Retriever
from evals.common import load_questions

LABEL_SET = Path(__file__).parent / "label_set.json"
OUT = RESULTS_DIR / "judge_answers.json"

# How many cases per slice (sums to 25). Spread wide, a bit heavier on the classic slices.
PER_SLICE = {"capability": 3, "exact_token": 3, "tier_gated": 3, "temporal": 3, "multi_hop": 3,
             "synthesis": 2, "non_official": 2, "conflict": 2, "out_of_scope": 2, "injection": 2}


def pick_ids(cases):
    by_class = defaultdict(list)
    for q in cases:
        by_class[q["class"]].append(q["id"])
    rng = random.Random(10)                       # fixed seed: the sample is reproducible
    ids = []
    for cls, n in PER_SLICE.items():
        pool = sorted(by_class[cls])
        ids += rng.sample(pool, min(n, len(pool)))
    return ids


def main():
    cases, _ = load_questions(split="dev", with_docs_only=False)   # refusals have no docs: keep them
    by_id = {q["id"]: q for q in cases}
    if LABEL_SET.exists():
        ids = json.loads(LABEL_SET.read_text())
        print(f"reusing {len(ids)} ids from {LABEL_SET.name}")
    else:
        ids = pick_ids(cases)
        LABEL_SET.write_text(json.dumps(ids, indent=2) + "\n")
        print(f"picked {len(ids)} ids -> {LABEL_SET.name}")

    retriever = Retriever()
    rows, total = [], 0.0
    for i, cid in enumerate(ids, 1):
        q = by_id[cid]
        out = answer(q["question"], retriever)
        total += out["cost"]
        rows.append({
            "id": cid, "class": q["class"], "question": q["question"],
            "golden": {k: q.get(k) for k in ("expected_behavior", "expected_answer", "expected_docs",
                                               "evidence", "must_include", "injected")},
            **out,
        })
        r = out["result"]
        print(f"{i:2d}. {cid:7s} {q['class']:13s} {r['status']:21s} {r['answer'][:70]!r}")
    retriever.close()

    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}  ({len(rows)} answers, total cost ${total:.4f})")


if __name__ == "__main__":
    main()
