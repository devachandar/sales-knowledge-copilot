# src2/retrieve.py
"""
Day 4, Lesson 3: find the top-k chunks for a question.

Run from src2/:
    python retrieve.py
"""

import os
import time

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from day3_embeddings import embed

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

SQL = """
SELECT chunk_id, doc_id, text, 1 - (embedding <=> %(q)s) AS score
FROM ip.chunks
WHERE strategy = %(strategy)s
ORDER BY embedding <=> %(q)s
LIMIT %(k)s
"""


def search(question, k=5, strategy="fixed-500"):
    """Returns (results, timings). Each result: chunk_id, doc_id, text, score."""
    t0 = time.perf_counter()
    q = embed([question], "RETRIEVAL_QUERY")[0]
    t1 = time.perf_counter()
    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        import numpy as np
        rows = conn.execute(SQL, {"q": np.array(q), "strategy": strategy, "k": k}).fetchall()
    t2 = time.perf_counter()
    results = [{"chunk_id": r[0], "doc_id": r[1], "text": r[2], "score": float(r[3])} for r in rows]
    timings = {"embed_ms": (t1 - t0) * 1000, "db_ms": (t2 - t1) * 1000}
    return results, timings


if __name__ == "__main__":
    TESTS = [
        ("Can clients pay invoices online themselves?", "client-portal/client-portal-overview"),
        ("Has BUG-2310-02 been fixed yet?", "invoicing/line-items-and-long-invoices"),
        ("How far back does the audit log go for Enterprise customers?", "account-billing/roles-and-audit-log"),
        ("How long does a new user have to accept their invite?", "getting-started/invite-users"),
    ]
    for question, expected in TESTS:
        results, t = search(question)
        hit = any(r["doc_id"] == expected for r in results)
        print(f"\n{'=' * 70}\nQ: {question}")
        print(f"expected: {expected} -> {'FOUND in top 5' if hit else 'MISSED'}")
        print(f"embed {t['embed_ms']:.0f} ms | db {t['db_ms']:.0f} ms")
        for i, r in enumerate(results, 1):
            mark = "  <-- expected" if r["doc_id"] == expected else ""
            print(f"  {i}. {r['score']:.3f}  {r['chunk_id']}{mark}")