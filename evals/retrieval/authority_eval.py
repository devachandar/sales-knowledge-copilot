# evals/retrieval/authority_eval.py
"""
Day 7, Lesson 4: relevance x authority x diversity, on the same 20 hybrid candidates.

Run from the project root:
    python -m evals.retrieval.authority_eval
"""

import os
from collections import defaultdict

import numpy as np
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import CrossEncoder

from copilot.retrieval.authority import diversify, hard_tiers, tier, with_authority
from copilot.retrieval.bm25 import load_index
from copilot.llm.embeddings import embed
from copilot.retrieval.fusion import rrf
from evals.common import load_questions
from evals.retrieval.hybrid_eval import SQL, STRATEGY, rank_of, summarize

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
K, FETCH, DEPTH = 5, 50, int(os.getenv("DEPTH", "20"))
MODEL = os.getenv("RERANKER", "cross-encoder/ms-marco-MiniLM-L-6-v2")


def systems_for(hyb_ids, hyb_scores, rr_ids, rr_scores, chunk):
    """Every combination we compare. Each value is a ranked list of chunk ids."""
    out = {}
    for name, ids, scores in (("hybrid", hyb_ids, hyb_scores), ("rerank", rr_ids, rr_scores)):
        auth = with_authority(ids, scores, chunk)
        out[name] = ids
        out[f"{name}+div"] = diversify(ids, chunk)
        out[f"{name}+auth"] = auth
        out[f"{name}+auth+div"] = diversify(auth, chunk)
        out[f"{name}+hard-tiers"] = hard_tiers(ids, scores, chunk)
    return out


def main():
    questions, _ = load_questions()
    index = load_index(STRATEGY)
    chunk = {c["chunk_id"]: c for c in index.chunks}
    reranker = CrossEncoder(MODEL)
    vectors = embed([q["question"] for q in questions], "RETRIEVAL_QUERY")

    ranks = defaultdict(lambda: defaultdict(list))
    tops = defaultdict(lambda: defaultdict(int))
    names = None

    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        for q, v in zip(questions, vectors):
            rows = conn.execute(SQL, {"q": np.array(v), "s": STRATEGY, "n": FETCH}).fetchall()
            fused = rrf([[r[0] for r in rows], [r["chunk_id"] for r in index.search(q["question"], k=FETCH)]])[:DEPTH]
            hyb_ids, hyb_scores = [c for c, _ in fused], [s for _, s in fused]

            rr = reranker.predict([(q["question"], chunk[c]["text"]) for c in hyb_ids])
            pairs = sorted(zip(rr, hyb_ids), key=lambda x: -x[0])
            rr_ids, rr_scores = [c for _, c in pairs], [float(s) for s, _ in pairs]

            expected = set(q["expected_docs"])
            systems = systems_for(hyb_ids, hyb_scores, rr_ids, rr_scores, chunk)
            names = list(systems)
            for name, ids in systems.items():
                r = rank_of([chunk[c]["doc_id"] for c in ids], expected)
                ranks[name][q["class"]].append(r)
                ranks[name]["ALL"].append(r)
                for c in ids[:K]:
                    tops[name][tier(chunk[c])] += 1

    for cls in ["exact_token", "tier_gated", "temporal", "capability", "ALL"]:
        if not ranks["hybrid"].get(cls):
            continue
        print(f"\n=== {cls} (n={len(ranks['hybrid'][cls])}) ===")
        for name in names:
            print(f"  {name:20s} {summarize(ranks[name][cls])}")

    print(f"\n=== who holds the top-{K} slots (official / internal / low) ===")
    for name in names:
        t = tops[name]
        total = sum(t.values())
        print(f"  {name:20s} {t['official'] / total:4.0%} / {t['internal'] / total:4.0%} / {t['low'] / total:4.0%}")


if __name__ == "__main__":
    main()