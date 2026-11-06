# src2/rerank_eval.py
"""
Day 7, Lesson 3: cross-encoder reranking. Hybrid top-N -> cross-encoder -> top 5.

Run from src2/:
    QUESTIONS=seed_questions.json,hard_questions.json,filter_questions.json,exact_questions.json python rerank_eval.py

Options (environment variables):
    RERANKER=cross-encoder/ms-marco-MiniLM-L-6-v2   (default, small and fast)
    RERANKER=BAAI/bge-reranker-base                 (bigger, slower)
    DEPTH=20                                        (how many hybrid candidates to rerank)
"""

import json
import os
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import CrossEncoder

from bm25 import load_index
from day3_embeddings import embed
from hybrid import rrf
from hybrid_eval import SQL, STRATEGY, rank_of, summarize

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
K, FETCH = 5, 50
DEPTH = int(os.getenv("DEPTH", "20"))
MODEL = os.getenv("RERANKER", "cross-encoder/ms-marco-MiniLM-L-6-v2")
SYSTEMS = ["hybrid", "hybrid+rerank"]


def main():
    files = os.getenv("QUESTIONS", "seed_questions.json").split(",")
    questions = [q for f in files for q in json.loads(Path(f).read_text(encoding="utf-8"))]
    index = load_index(STRATEGY)
    chunk = {c["chunk_id"]: c for c in index.chunks}
    print(f"loading reranker {MODEL} ...")
    reranker = CrossEncoder(MODEL)
    vectors = embed([q["question"] for q in questions], "RETRIEVAL_QUERY")

    ranks = {s: defaultdict(list) for s in SYSTEMS}
    slots = {s: defaultdict(int) for s in SYSTEMS}
    latency, changes = [], []

    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        for q, v in zip(questions, vectors):
            rows = conn.execute(SQL, {"q": np.array(v), "s": STRATEGY, "n": FETCH}).fetchall()
            vec = [r[0] for r in rows]
            lex = [r["chunk_id"] for r in index.search(q["question"], k=FETCH)]
            hybrid = [cid for cid, _ in rrf([vec, lex])]

            # Rerank: read each candidate TOGETHER with the question, one model run per pair.
            candidates = hybrid[:DEPTH]
            t0 = time.perf_counter()
            scores = reranker.predict([(q["question"], chunk[c]["text"]) for c in candidates])
            latency.append((time.perf_counter() - t0) * 1000)
            reranked = [c for _, c in sorted(zip(scores, candidates), key=lambda x: -x[0])]

            expected = set(q["expected_docs"])
            got = {}
            for s, lst in (("hybrid", hybrid), ("hybrid+rerank", reranked)):
                r = rank_of([chunk[c]["doc_id"] for c in lst], expected)
                got[s] = r
                ranks[s][q["class"]].append(r)
                ranks[s]["ALL"].append(r)
                for c in lst[:K]:
                    slots[s][chunk[c]["source_type"]] += 1
            if got["hybrid"] != got["hybrid+rerank"]:
                top = chunk[reranked[0]]
                changes.append(f"  {q['id']:6s} hybrid {str(got['hybrid']):>4s} -> rerank {str(got['hybrid+rerank']):>4s}"
                               f"   new #1: {top['source_type']:16s} {top['chunk_id'][:40]}")

    print(f"\nreranker: {MODEL}, depth {DEPTH}")
    for cls in ["exact_token", "tier_gated", "temporal", "capability", "ALL"]:
        if not ranks["hybrid"].get(cls):
            continue
        print(f"\n=== {cls} (n={len(ranks['hybrid'][cls])}) ===")
        for s in SYSTEMS:
            print(f"  {s:14s} {summarize(ranks[s][cls])}")

    print(f"\n=== share of top-{K} slots held by support tickets ===")
    for s in SYSTEMS:
        total = sum(slots[s].values())
        print(f"  {s:14s} {slots[s]['support_ticket'] / total:.0%}")

    lat = np.array(latency)
    print(f"\nrerank latency per question ({DEPTH} pairs): median {np.median(lat):.0f} ms, "
          f"p95 {np.percentile(lat, 95):.0f} ms, max {lat.max():.0f} ms")
    print("(the first question includes model warm-up)")

    print("\n=== questions whose rank changed ===")
    print("\n".join(changes))


if __name__ == "__main__":
    main()