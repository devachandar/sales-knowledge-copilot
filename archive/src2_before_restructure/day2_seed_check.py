# src2/day2_seed_check.py
"""Check seed_questions.json for mistakes. Run from src2/: python day2_seed_check.py"""

import json
from collections import Counter
import os
from pathlib import Path

from day2_grounded import HELP_CENTER

CLASSES = {"capability", "exact_token", "tier_gated", "temporal", "non_official"}
REQUIRED = {"id", "class", "question", "expected_answer", "expected_docs", "must_include", "difficulty"}
DOCS = {json.loads(l)["doc_id"]: json.loads(l)["text"]
        for l in open("../data/invoicepilot/processed/documents.jsonl", encoding="utf-8")}

FILES = os.getenv("QUESTIONS", "seed_questions.json").split(",")
seeds = [q for f in FILES for q in json.loads(Path(f).read_text(encoding="utf-8"))]
print("files:", FILES)
problems = []

ids = Counter(s.get("id") for s in seeds)
problems += [f"duplicate id {i}" for i, n in ids.items() if n > 1]

for s in seeds:
    sid = s.get("id", "?")
    if missing := REQUIRED - s.keys():
        problems.append(f"{sid}: missing fields {sorted(missing)}")
        continue
    if s["class"] not in CLASSES:
        problems.append(f"{sid}: unknown class {s['class']!r}")
    for d in s["expected_docs"]:
        if d not in DOCS:
            problems.append(f"{sid}: expected doc not found: {d}")
            continue
        for word in s["must_include"]:
            if word.lower() not in DOCS[d].lower():
                problems.append(f"{sid}: {word!r} is not on {d}")

print(f"{len(seeds)} questions")
print("by class:", dict(Counter(s.get("class") for s in seeds)))
print("by difficulty:", dict(Counter(s.get("difficulty") for s in seeds)))
print("problems:" if problems else "no problems found")
for p in problems:
    print("  -", p)