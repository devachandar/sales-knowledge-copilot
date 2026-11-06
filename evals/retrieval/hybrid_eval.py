# evals/retrieval/hybrid_eval.py
"""
Day 7, Lesson 2: vector alone vs BM25 alone vs hybrid (RRF), same questions, same run.

Run from the project root:
    python -m evals.retrieval.hybrid_eval
"""

import os
from collections import defaultdict

import numpy as np
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from copilot.retrieval.bm25 import load_index
from copilot.llm.embeddings import embed
from copilot.retrieval.fusion import rrf
from evals.common import load_questions

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
STRATEGY, K, FETCH = "structure-aware", 5, 50
SYSTEMS = ["vector", "bm25", "hybrid"]

SQL = """
SELECT chunk_id, doc_id, metadata->>'source_type'
FROM ip.chunks WHERE strategy = %(s)s
ORDER BY embedding <=> %(q)s LIMIT %(n)s
"""


def rank_of(doc_ids, expected):
    return next((i + 1 for i, d in enumerate(doc_ids) if d in expected), None)


def summarize(rows):
    n = len(rows)
    r1 = sum(r == 1 for r in rows) / n
    r5 = sum(r is not None and r <= K for r in rows) / n
    r20 = sum(r is not None and r <= 20 for r in rows) / n
    mrr = sum(1 / r for r in rows if r and r <= K) / n
    return f"r@1 {r1:4.0%}  r@5 {r5:4.0%}  r@20 {r20:4.0%}  MRR {mrr:.2f}"


def main():
    questions, _ = load_questions()
    index = load_index(STRATEGY)
    vectors = embed([q["question"] for q in questions], "RETRIEVAL_QUERY")

    info = {c["chunk_id"]: (c["doc_id"], c["source_type"]) for c in index.chunks}
    ranks = {s: defaultdict(list) for s in SYSTEMS}
    slots = {s: defaultdict(int) for s in SYSTEMS}
    changes = []

    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        for q, v in zip(questions, vectors):
            rows = conn.execute(SQL, {"q": np.array(v), "s": STRATEGY, "n": FETCH}).fetchall()
            for chunk_id, doc_id, stype in rows:
                info[chunk_id] = (doc_id, stype)
            lists = {
                "vector": [r[0] for r in rows],
                "bm25": [r["chunk_id"] for r in index.search(q["question"], k=FETCH)],
            }
            lists["hybrid"] = [cid for cid, _ in rrf([lists["vector"], lists["bm25"]])][:FETCH]

            expected = set(q["expected_docs"])
            got = {}
            for s in SYSTEMS:
                r = rank_of([info[c][0] for c in lists[s]], expected)
                got[s] = r
                ranks[s][q["class"]].append(r)
                ranks[s]["ALL"].append(r)
                for c in lists[s][:K]:
                    slots[s][info[c][1]] += 1
            if got["hybrid"] != got["vector"]:
                changes.append(f"  {q['id']:6s} vector {str(got['vector']):>4s}  bm25 {str(got['bm25']):>4s}"
                               f"  -> hybrid {str(got['hybrid']):>4s}")

    for cls in ["exact_token", "tier_gated", "temporal", "capability", "ALL"]:
        if not ranks["vector"].get(cls):
            continue
        print(f"\n=== {cls} (n={len(ranks['vector'][cls])}) ===")
        for s in SYSTEMS:
            print(f"  {s:7s} {summarize(ranks[s][cls])}")

    print(f"\n=== share of top-{K} slots held by support tickets ===")
    for s in SYSTEMS:
        total = sum(slots[s].values())
        print(f"  {s:7s} {slots[s]['support_ticket'] / total:.0%}")

    print("\n=== questions where hybrid's rank differs from vector's ===")
    print("\n".join(changes))


if __name__ == "__main__":
    main()