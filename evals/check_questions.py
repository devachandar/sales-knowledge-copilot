# evals/check_questions.py
"""Check the question files for mistakes.

Run from the project root:
    python -m evals.check_questions                 # all five files
    QUESTIONS=seed,hard python -m evals.check_questions
"""

import json
from collections import Counter

from copilot.config import DOCUMENTS_FILE
from evals.common import load_questions

CLASSES = {"capability", "exact_token", "tier_gated", "temporal", "non_official"}
REQUIRED = {"id", "class", "question", "expected_answer", "expected_docs", "must_include", "difficulty"}
DOCS = {json.loads(l)["doc_id"]: json.loads(l)["text"]
        for l in open(DOCUMENTS_FILE, encoding="utf-8")}

seeds, FILES = load_questions()
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