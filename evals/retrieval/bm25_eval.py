# evals/retrieval/bm25_eval.py
"""
Day 7, Lesson 1: how good is BM25 ALONE? Retrieval only, no answers, no API calls.

Run from the project root:
    python -m evals.retrieval.bm25_eval
"""

from collections import defaultdict

from copilot.retrieval.bm25 import load_index
from evals.common import load_questions

K, FETCH = 5, 50
WATCH = ["e-02", "e-07", "c2-06"]       # the look-alike-token misses from the diagnosis


def main():
    questions, _ = load_questions()
    index = load_index()

    by_class = defaultdict(list)
    for q in questions:
        results = index.search(q["question"], k=FETCH)
        expected = set(q["expected_docs"])
        rank = next((i + 1 for i, r in enumerate(results) if r["doc_id"] in expected), None)
        row = {"id": q["id"], "rank": rank, "top": results[:K]}
        by_class[q["class"]].append(row)
        by_class["ALL"].append(row)

    print(f"BM25 alone, k={K}")
    for cls in ["exact_token", "tier_gated", "temporal", "capability", "ALL"]:
        rows = by_class.get(cls, [])
        if not rows:
            continue
        n = len(rows)
        r1 = sum(r["rank"] == 1 for r in rows) / n
        r5 = sum(r["rank"] is not None and r["rank"] <= K for r in rows) / n
        mrr = sum(1 / r["rank"] for r in rows if r["rank"] and r["rank"] <= K) / n
        print(f"  {cls:12s} n={n:2d}  r@1 {r1:4.0%}  r@5 {r5:4.0%}  MRR {mrr:.2f}")

    slots = defaultdict(int)
    for r in by_class["ALL"]:
        for c in r["top"]:
            slots[c["source_type"]] += 1
    total = sum(slots.values())
    print("\nshare of top-5 slots:", ", ".join(f"{t} {n / total:.0%}" for t, n in sorted(slots.items(), key=lambda x: -x[1])))

    print("\nlook-alike-token questions (vector search put the WRONG code at #1):")
    for r in by_class["ALL"]:
        if r["id"] in WATCH:
            print(f"  {r['id']}: official at {r['rank']}, #1 = {r['top'][0]['chunk_id']}")


if __name__ == "__main__":
    main()