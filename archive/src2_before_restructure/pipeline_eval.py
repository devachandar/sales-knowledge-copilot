# src2/pipeline_eval.py
"""
Day 8: V1 to V4 on the same corpus, the same questions, the same metrics. This is the results table.

Run from src2/:
    python pipeline_eval.py
"""

import json
import os
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from day3_embeddings import embed
from pipeline import K, VERSIONS, Retriever

FILES = os.getenv("QUESTIONS", "seed_questions.json,hard_questions.json,filter_questions.json,"
                               "exact_questions.json,nonofficial_questions.json").split(",")
CLASSES = ["capability", "exact_token", "tier_gated", "temporal", "non_official", "ALL"]
OUT = Path("../data/invoicepilot/results/pipeline_v1_v4.json")


def main():
    questions = [q for f in FILES for q in json.loads(Path(f).read_text(encoding="utf-8"))]
    t0 = time.perf_counter()
    vectors = embed([q["question"] for q in questions], "RETRIEVAL_QUERY")
    embed_ms = (time.perf_counter() - t0) * 1000 / len(questions)

    r = Retriever()
    ranks = {v: defaultdict(list) for v in VERSIONS}
    latency = {v: [] for v in VERSIONS}
    per_question = {v: {} for v in VERSIONS}

    for v in VERSIONS:
        for q, qvec in zip(questions, vectors):
            t = time.perf_counter()
            top = r.retrieve(q["question"], version=v, k=K, qvec=qvec)
            latency[v].append((time.perf_counter() - t) * 1000)
            expected = set(q["expected_docs"])
            rank = next((i + 1 for i, c in enumerate(top) if c["doc_id"] in expected), None)
            ranks[v][q["class"]].append(rank)
            ranks[v]["ALL"].append(rank)
            per_question[v][q["id"]] = {"rank": rank, "top": [c["chunk_id"] for c in top]}
    r.close()

    def score(rows):
        n = len(rows)
        return {"n": n,
                "r@1": sum(x == 1 for x in rows) / n,
                "r@5": sum(x is not None for x in rows) / n,
                "mrr": sum(1 / x for x in rows if x) / n}

    table = {v: {c: score(ranks[v][c]) for c in CLASSES if ranks[v][c]} for v in VERSIONS}

    for metric in ["r@5", "r@1"]:
        print(f"\n| {metric} | " + " | ".join(VERSIONS) + " |")
        print("|---|" + "---|" * len(VERSIONS))
        for c in CLASSES:
            if c in table["V1"]:
                cells = " | ".join(f"{table[v][c][metric]:.0%}" for v in VERSIONS)
                print(f"| {c} (n={table['V1'][c]['n']}) | {cells} |")

    print(f"\nlatency per question (retrieval only; embedding adds about {embed_ms:.0f} ms, measured as a batch)")
    for v in VERSIONS:
        lat = np.array(latency[v][1:])      # skip the first call: connection / model warm-up
        print(f"  {v}: median {np.median(lat):.0f} ms, p95 {np.percentile(lat, 95):.0f} ms")

    OUT.write_text(json.dumps({"versions": VERSIONS, "files": FILES, "table": table,
                               "latency_ms": {v: {"median": float(np.median(latency[v][1:])),
                                                  "p95": float(np.percentile(latency[v][1:], 95))}
                                              for v in VERSIONS},
                               "per_question": per_question}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()