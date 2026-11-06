# evals/retrieval/chunking_baseline.py
"""
Day 4: run a question set through the full pipeline and record the results.

Run from the project root:
    python -m evals.retrieval.chunking_baseline                                                      # seed set
    QUESTIONS=hard RUN_NAME=baseline_v1_hard python -m evals.retrieval.chunking_baseline
"""

import json
import os
import statistics
from collections import defaultdict
from datetime import datetime

from copilot.generation.answer import rag_answer
from copilot.config import RESULTS_DIR
from copilot.generation.grounded import PROMPT_VERSION
from evals.common import load_questions

STRATEGY = os.getenv("STRATEGY", "fixed-500")
K = 5
QUESTIONS = os.getenv("QUESTIONS", "seed")
RUN_NAME = os.getenv("RUN_NAME", "baseline_v1")
OUT = RESULTS_DIR / f"{RUN_NAME}.json"

seeds, _ = load_questions(QUESTIONS)
rows = []

for s in seeds:
    out = rag_answer(s["question"], k=K, strategy=STRATEGY)
    r = out["result"]
    retrieved = out["retrieved"]
    ranks = [i + 1 for i, x in enumerate(retrieved) if x["doc_id"] in s["expected_docs"]]
    hit = bool(ranks)

    right = [x["score"] for x in retrieved if x["doc_id"] in s["expected_docs"]]
    wrong = [x["score"] for x in retrieved if x["doc_id"] not in s["expected_docs"]]
    margin = (max(right) - max(wrong)) if right and wrong else None

    missing = [w for w in s["must_include"] if w.lower() not in r["answer"].lower()]
    correct = r["status"] == "answered" and not missing and not out["problems"]
    bucket = "ok" if correct else ("retrieval_miss" if not hit else "generation_miss")

    rows.append({
        "id": s["id"], "class": s["class"], "question": s["question"],
        "expected_docs": s["expected_docs"],
        "retrieved": [x["chunk_id"] for x in retrieved],
        "scores": [round(x["score"], 4) for x in retrieved],
        "hit": hit, "first_hit_rank": ranks[0] if ranks else None, "margin": margin,
        "status": r["status"], "answer": r["answer"], "citations": r["citations"],
        "missing": missing, "problems": out["problems"],
        "correct": correct, "bucket": bucket,
        "timings": out["timings"], "tokens_in": out["tokens_in"],
        "tokens_out": out["tokens_out"], "cost": out["cost"],
    })
    m = f"{margin:+.3f}" if margin is not None else "  n/a "
    print(f"[{bucket:15s}] {s['id']}  rank={ranks[0] if ranks else '-'}  margin={m}  {s['question'][:55]}")

# ---- summary --------------------------------------------------------------
by_class = defaultdict(list)
for row in rows:
    by_class[row["class"]].append(row)

print(f"\n{'class':12s} {'n':>3s} {'recall@1':>9s} {'recall@5':>9s} {'MRR':>6s} {'correct':>8s}")
summary = {}
for cls, group in list(by_class.items()) + [("ALL", rows)]:
    n = len(group)
    r1 = sum(g["first_hit_rank"] == 1 for g in group) / n
    r5 = sum(g["hit"] for g in group) / n
    mrr = sum(1 / g["first_hit_rank"] for g in group if g["first_hit_rank"]) / n
    cor = sum(g["correct"] for g in group) / n
    summary[cls] = {"n": n, "recall@1": r1, "recall@5": r5, "mrr": mrr, "correct": cor}
    print(f"{cls:12s} {n:>3d} {r1:>9.0%} {r5:>9.0%} {mrr:>6.2f} {cor:>8.0%}")

margins = sorted((r["margin"], r["id"]) for r in rows if r["margin"] is not None)
print("\nclosest calls (smallest margin):", [(i, round(m, 3)) for m, i in margins[:5]])

total = [sum(r["timings"].values()) for r in rows]
cost = sum(r["cost"] for r in rows)
print(f"latency: median {statistics.median(total):.0f} ms, max {max(total):.0f} ms")
print(f"cost: ${cost:.4f} total, ${cost / len(rows):.5f} per question")
print("buckets:", {b: sum(r["bucket"] == b for r in rows) for b in ("ok", "retrieval_miss", "generation_miss")})

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "run": RUN_NAME, "questions": QUESTIONS,
    "date": datetime.now().isoformat(timespec="seconds"),
    "config": {"strategy": STRATEGY, "k": K, "prompt": PROMPT_VERSION,
               "chat_model": "gemini-3.5-flash-lite", "embed_model": "gemini-embedding-001", "dims": 768},
    "summary": summary,
    "latency_ms": {"median": statistics.median(total), "max": max(total)},
    "cost_usd": {"total": cost, "per_question": cost / len(rows)},
    "rows": rows,
}, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")