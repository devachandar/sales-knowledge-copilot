# evals/retrieval/evidence_recall.py
"""
Day 11, step 1: evidence-level retrieval metrics.

Doc-level recall (Day 8) counts a hit if ANY expected document is in the top 5. That overstates
multi-hop, synthesis and conflict, which need two or more pieces. Here we check the golden
EVIDENCE QUOTES instead: which of them appear inside the top-5 chunks?

    doc r@5    any expected doc in the top 5                      (old, an upper bound)
    ev recall  share of evidence quotes found in the top 5        (context recall)
    full ev    all quotes found: the answer is fully possible     (strict, a lower bound)
    ctx prec   share of the 5 chunks that hold at least one quote  (context precision)

No model calls: it re-scores the top-5 chunk ids already saved by run_pipeline.py.

Run from the project root (after python -m evals.retrieval.run_pipeline):
    python -m evals.retrieval.evidence_recall
"""

import json
import re
from collections import defaultdict

from copilot.config import RESULTS_DIR, chunks_file
from evals.common import load_questions

PIPELINE = RESULTS_DIR / "pipeline_v1_v4.json"
STRATEGY = {"V1": "fixed-500", "V2": "structure-aware", "V3": "structure-aware", "V4": "structure-aware"}
CLASSES = ["capability", "exact_token", "tier_gated", "temporal", "multi_hop", "synthesis",
           "conflict", "injection", "non_official", "ALL"]


def norm(s):
    """Lowercase, drop markdown marks, squash whitespace, so formatting never hides a match."""
    return re.sub(r"\s+", " ", re.sub(r"[*_`>#]|\\", "", s.lower())).strip()


def load_chunks(strategy):
    with open(chunks_file(strategy), encoding="utf-8") as f:
        return {c["chunk_id"]: norm(c["text"]) for c in map(json.loads, f)}


def score_question(q, texts):
    quotes = [norm(e) for e in q["evidence"]]
    found = [any(e in t for t in texts) for e in quotes]
    useful = [any(e in t for e in quotes) for t in texts]
    return {"found": found, "ev": sum(found) / len(found), "full": all(found),
            "prec": sum(useful) / len(useful) if useful else 0.0}


def main():
    saved = json.loads(PIPELINE.read_text())
    questions, _ = load_questions()
    by_id = {q["id"]: q for q in questions}
    chunks = {s: load_chunks(s) for s in set(STRATEGY.values())}

    # every quote should exist in SOME chunk; if not, chunking split it and no retriever can find it
    for s, texts in chunks.items():
        lost = [(q["id"], e) for q in questions for e in q["evidence"]
                if not any(norm(e) in t for t in texts.values())]
        print(f"{s}: {len(lost)} evidence quotes not inside any single chunk" + (f" {lost[:5]}" if lost else ""))

    out = {}
    for v, per_q in saved["per_question"].items():
        agg = defaultdict(lambda: defaultdict(list))
        rows = {}
        for qid, r in per_q.items():
            if qid not in by_id:
                continue                      # saved run used other questions or another split
            q = by_id[qid]
            s = score_question(q, [chunks[STRATEGY[v]][c] for c in r["top"]])
            s["doc"] = r["rank"] is not None
            rows[qid] = s
            for k in (q["class"], "ALL"):
                for m in ("doc", "ev", "full", "prec"):
                    agg[k][m].append(float(s[m]))
        out[v] = {"rows": rows, "table": {k: {m: sum(x) / len(x) for m, x in a.items()} | {"n": len(a["doc"])}
                                          for k, a in agg.items()}}

        print(f"\n{v}  {'class':14s} {'n':>3s} {'doc r@5':>8s} {'ev recall':>10s} {'full ev':>8s} {'ctx prec':>9s}")
        for k in CLASSES:
            t = out[v]["table"].get(k)
            if t:
                print(f"    {k:14s} {t['n']:3d} {t['doc']:8.0%} {t['ev']:10.0%} {t['full']:8.0%} {t['prec']:9.0%}")

    gap = [qid for qid, s in out["V4"]["rows"].items() if s["doc"] and not s["full"]]
    print(f"\nV4: {len(gap)} questions count as a doc hit but miss at least one evidence quote:")
    print("  " + ", ".join(gap))

    dest = RESULTS_DIR / "evidence_recall_dev.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
