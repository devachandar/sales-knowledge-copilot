# evals/retrieval/diagnose.py
"""
Day 7: why did retrieval drop on corpus v2? Retrieval only, no answers.

Run from the project root:
    python -m evals.retrieval.diagnose
"""

import os
from collections import Counter

import numpy as np
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from copilot.llm.embeddings import embed
from evals.common import load_questions

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
STRATEGY, K, FETCH = "structure-aware", 5, 50

SQL = """
SELECT chunk_id, doc_id, metadata, 1 - (embedding <=> %(q)s) AS score
FROM ip.chunks WHERE strategy = %(s)s
ORDER BY embedding <=> %(q)s LIMIT %(n)s
"""
COUNT_SQL = "SELECT metadata->>'source_type', count(*) FROM ip.chunks WHERE strategy = %(s)s GROUP BY 1"


def main():
    questions, _ = load_questions()
    vectors = embed([q["question"] for q in questions], "RETRIEVAL_QUERY")

    slots = Counter()        # who holds the top-5 slots, over all questions
    winners = Counter()      # who holds rank 1 when the official page does NOT
    dup_runs = 0             # top-5 lists with 2+ tickets that share a subject
    lines = []

    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        pool = dict(conn.execute(COUNT_SQL, {"s": STRATEGY}).fetchall())
        for q, v in zip(questions, vectors):
            rows = conn.execute(SQL, {"q": np.array(v), "s": STRATEGY, "n": FETCH}).fetchall()
            top = [{"doc_id": r[1], "type": r[2].get("source_type"), "title": r[2].get("title", ""),
                    "score": float(r[3])} for r in rows]
            expected = set(q["expected_docs"])
            for r in top[:K]:
                slots[r["type"]] += 1
            subjects = Counter(r["title"] for r in top[:K] if r["type"] == "support_ticket")
            if any(n >= 2 for n in subjects.values()):
                dup_runs += 1

            best = next((i + 1 for i, r in enumerate(top) if r["doc_id"] in expected), None)
            if best != 1:
                winners[top[0]["type"]] += 1
                gap = (top[0]["score"] - top[best - 1]["score"]) if best else None
                lines.append(
                    f"{q['id']:6s} {q['class']:12s} official at {str(best):>4s}   "
                    f"#1 = {top[0]['type']:16s} {top[0]['doc_id'][:42]:42s} "
                    + (f"gap {gap:.3f}" if gap is not None else "not in top 50")
                    + "\n        top5: " + ", ".join(r["type"] for r in top[:K]))

    total = sum(pool.values())
    print(f"\n=== chunk pool ({total} chunks) vs share of top-{K} slots ({len(questions) * K} slots) ===")
    for t, n in sorted(pool.items(), key=lambda x: -x[1]):
        print(f"  {t:18s} pool {n / total:5.0%}   top-{K} slots {slots[t] / (len(questions) * K):5.0%}")

    print(f"\n=== who takes rank 1 when the official page doesn't ({sum(winners.values())} questions) ===")
    for t, n in winners.most_common():
        print(f"  {t:18s} {n}")

    print(f"\ntop-{K} lists with 2+ tickets on the same subject: {dup_runs}/{len(questions)}")

    print("\n=== every question that misses r@1 ===")
    print("\n".join(lines))


if __name__ == "__main__":
    main()