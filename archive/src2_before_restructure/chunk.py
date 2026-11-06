# src2/chunk.py
"""
Day 5: chunk documents.jsonl with a chosen strategy.

Run from src2/:
    STRATEGY=recursive-500 python chunk.py
"""

import json
import os
from collections import Counter
from pathlib import Path

from chunkers import STRATEGIES

DATA = Path("../data/invoicepilot/processed")
STRATEGY = os.getenv("STRATEGY", "fixed-500")
META_FIELDS = ["title", "source_type", "source_path", "section",
               "last_updated", "applies_to", "plans", "version", "author"]


def main():
    split = STRATEGIES[STRATEGY]
    docs = [json.loads(l) for l in open(DATA / "documents.jsonl", encoding="utf-8")]
    rows = []
    for d in docs:
        for i, piece in enumerate(split(d["text"], d["title"])):
            rows.append({"chunk_id": f"{d['doc_id']}#{i}", "doc_id": d["doc_id"],
                         "strategy": STRATEGY, "text": piece,
                         **{k: d.get(k) for k in META_FIELDS}})

    out = DATA / f"chunks_{STRATEGY}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    per_doc = Counter(r["doc_id"] for r in rows)
    lengths = sorted(len(r["text"]) for r in rows)
    print(f"strategy {STRATEGY}: {len(docs)} documents -> {len(rows)} chunks")
    print(f"docs with only 1 chunk: {sum(1 for n in per_doc.values() if n == 1)}")
    print(f"chunk length: shortest {lengths[0]}, median {lengths[len(lengths) // 2]}, longest {lengths[-1]}")
    print(f"wrote {out}\n")

    for doc_id in ["account-billing/plans-and-limits", "release-notes/v2.3.1"]:
        print("=" * 70, f"\n{doc_id}")
        for r in rows:
            if r["doc_id"] == doc_id:
                print(f"\n--- {r['chunk_id']} ({len(r['text'])} chars) ---\n{r['text']}")


if __name__ == "__main__":
    main()