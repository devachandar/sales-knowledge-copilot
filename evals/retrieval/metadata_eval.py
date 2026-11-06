# evals/retrieval/metadata_eval.py
"""
Day 6, Lesson 3: compare metadata filtering modes on retrieval only (no answers).

Run from the project root:
    python filtered_search.py
"""

import os
from collections import defaultdict

import numpy as np
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from copilot.llm.embeddings import embed
from copilot.retrieval.metadata import FETCH, MODES, apply_mode
from copilot.retrieval.query_filters import rule_filters
from evals.common import load_questions

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
STRATEGY = "structure-aware"

SQL = """
SELECT chunk_id, doc_id, metadata, 1 - (embedding <=> %(q)s) AS score
FROM ip.chunks WHERE strategy = %(s)s
ORDER BY embedding <=> %(q)s LIMIT %(n)s
"""


def metrics(results, expected):
    ranks = [i + 1 for i, r in enumerate(results) if r["doc_id"] in expected]
    right = [r["score"] for r in results if r["doc_id"] in expected]
    wrong = [r["score"] for r in results if r["doc_id"] not in expected]
    return {"rank": ranks[0] if ranks else None,
            "neg": bool(right and wrong and max(wrong) > max(right))}


def main():
    questions, _ = load_questions()
    vectors = embed([q["question"] for q in questions], "RETRIEVAL_QUERY")   # one batch call

    rows = defaultdict(list)          # mode -> list of (question, metrics)
    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        for q, vec in zip(questions, vectors):
            cand = [{"chunk_id": r[0], "doc_id": r[1], "metadata": r[2], "score": float(r[3])}
                    for r in conn.execute(SQL, {"q": np.array(vec), "s": STRATEGY, "n": FETCH})]
            filt = rule_filters(q["question"])
            for mode in MODES:
                rows[mode].append((q, filt, metrics(apply_mode(cand, filt, mode), q["expected_docs"])))

    def summarize(items):
        n = len(items)
        r1 = sum(m["rank"] == 1 for _, _, m in items) / n
        r5 = sum(m["rank"] is not None for _, _, m in items) / n
        mrr = sum(1 / m["rank"] for _, _, m in items if m["rank"]) / n
        neg = sum(m["neg"] for _, _, m in items)
        return f"r@1 {r1:4.0%}  r@5 {r5:4.0%}  MRR {mrr:.2f}  neg {neg}"

    for group in ["exact_token", "tier_gated", "temporal", "ALL"]:
        print(f"\n=== {group} ===")
        for mode in MODES:
            items = [x for x in rows[mode] if group == "ALL" or x[0]["class"] == group]
            print(f"  {mode:18s} n={len(items):2d}  {summarize(items)}")

    print("\n=== questions whose rank changed vs 'none' ===")
    base = {q["id"]: m["rank"] for q, _, m in rows["none"]}
    for mode in MODES[1:]:
        for q, filt, m in rows[mode]:
            if m["rank"] != base[q["id"]]:
                print(f"  {mode:18s} {q['id']:6s} rank {base[q['id']]} -> {m['rank']}   filter {filt}")


if __name__ == "__main__":
    main()