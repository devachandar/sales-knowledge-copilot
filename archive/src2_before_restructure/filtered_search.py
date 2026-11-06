# src2/filtered_search.py
"""
Day 6, Lesson 3: compare metadata filtering modes on retrieval only (no answers).

Run from src2/:
    python filtered_search.py
"""

import json
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from day3_embeddings import embed
from filters import rule_filters

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
STRATEGY = "structure-aware"
K, FETCH, BOOST = 5, 50, 0.02
MODES = ["none", "no-community", "hard", "hard+no-community", "soft", "soft+no-community"]

SQL = """
SELECT chunk_id, doc_id, metadata, 1 - (embedding <=> %(q)s) AS score
FROM ip.chunks WHERE strategy = %(s)s
ORDER BY embedding <=> %(q)s LIMIT %(n)s
"""


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def covers_version(applies, version):
    """'2.3.0+' = that version and later; '2.1.0' = exactly; empty = everything."""
    if version == "none" or not applies:
        return True
    try:
        if applies.endswith("+"):
            return vtuple(version) >= vtuple(applies[:-1])
        return vtuple(version) == vtuple(applies)
    except ValueError:
        return True                       # a label we can't read: never filter on it


def covers_plan(plans, plan):
    return plan == "none" or not plans or plan in plans


def apply_mode(candidates, filt, mode):
    out = []
    for c in candidates:
        m = c["metadata"]
        community = m.get("source_type") == "community"
        match = covers_version(m.get("applies_to"), filt["version"]) and covers_plan(m.get("plans"), filt["plan"])
        if "no-community" in mode and community:
            continue
        if mode.startswith("hard") and not match:
            continue
        score = c["score"]
        if mode.startswith("soft"):
            score += BOOST if (match and filt != {"version": "none", "plan": "none"}) else 0
            score -= BOOST if community else 0
        out.append({**c, "score": score})
    return sorted(out, key=lambda x: x["score"], reverse=True)[:K]


def metrics(results, expected):
    ranks = [i + 1 for i, r in enumerate(results) if r["doc_id"] in expected]
    right = [r["score"] for r in results if r["doc_id"] in expected]
    wrong = [r["score"] for r in results if r["doc_id"] not in expected]
    return {"rank": ranks[0] if ranks else None,
            "neg": bool(right and wrong and max(wrong) > max(right))}


def main():
    files = os.getenv("QUESTIONS", "seed_questions.json,hard_questions.json").split(",")
    questions = [q for f in files for q in json.loads(Path(f).read_text())]
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