# evals/check_questions.py
"""
Check the golden set for mistakes, then print its composition table.

Run from the project root:
    python -m evals.check_questions                 # all question sets
    QUESTIONS=seed,hard python -m evals.check_questions

Exits with status 1 if any problem is found, so it can guard a commit or CI later.
"""

import json
import re
import sys
from collections import Counter, defaultdict

from copilot.config import DOCUMENTS_FILE
from evals.common import load_questions

CLASSES = ["capability", "exact_token", "tier_gated", "temporal", "multi_hop", "synthesis",
           "out_of_scope", "conflict", "injection", "non_official"]
BEHAVIORS = {"answer", "refuse", "flag_conflict", "resist"}
SPLITS = {"dev", "test"}
DIFFICULTY = {"easy", "medium", "hard"}
REQUIRED = {"id", "class", "question", "expected_behavior", "expected_answer", "expected_docs",
            "evidence", "must_include", "difficulty", "targets", "split", "verified"}

DOCS = {json.loads(l)["doc_id"]: json.loads(l)["text"] for l in open(DOCUMENTS_FILE, encoding="utf-8")}


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def check_case(q):
    p = []
    if missing := REQUIRED - q.keys():
        return [f"missing fields {sorted(missing)}"]
    if q["class"] not in CLASSES:
        p.append(f"unknown class {q['class']!r}")
    if q["expected_behavior"] not in BEHAVIORS:
        p.append(f"unknown expected_behavior {q['expected_behavior']!r}")
    if q["split"] not in SPLITS:
        p.append(f"unknown split {q['split']!r}")
    if q["difficulty"] not in DIFFICULTY:
        p.append(f"unknown difficulty {q['difficulty']!r}")
    if not isinstance(q["verified"], bool):
        p.append("verified must be true or false")
    if not q["targets"]:
        p.append("targets is empty: tag the failure this case tests")

    for d in q["expected_docs"]:
        if d not in DOCS:
            p.append(f"expected doc not found: {d}")
    texts = [DOCS[d] for d in q["expected_docs"] if d in DOCS]

    # 1. every evidence quote must appear word for word in an expected doc
    quote_docs = []
    for quote in q["evidence"]:
        where = [d for d in q["expected_docs"] if d in DOCS and quote in DOCS[d]]
        if not where:
            p.append(f"evidence quote not found in any expected doc: {quote[:70]!r}")
        quote_docs.append(set(where))

    # 2. must_include is the core fact: it must be in the expected answer and in the docs
    for word in q["must_include"]:
        if word.lower() not in q["expected_answer"].lower():
            p.append(f"must_include {word!r} is not in expected_answer")
        if q["expected_behavior"] in ("answer", "flag_conflict") and not any(word.lower() in t.lower() for t in texts):
            p.append(f"must_include {word!r} is not on any expected doc")

    # 3. behavior-specific rules
    b = q["expected_behavior"]
    if b in ("answer", "flag_conflict") and not q["evidence"]:
        p.append("answerable case has no evidence quote")
    if b == "refuse" and q["expected_docs"]:
        p.append("refuse case should have no expected_docs (nothing should be cited)")
    if b == "flag_conflict":
        if len(q["expected_docs"]) < 2:
            p.append("conflict case needs at least two expected_docs")
        if len(set().union(*quote_docs) if quote_docs else set()) < 2:
            p.append("conflict case needs evidence quotes from at least two different docs")
    if b == "resist" and not q.get("injected"):
        p.append("resist case needs an 'injected' field with the attack text")
    return p


def main():
    cases, files = load_questions(split="all", with_docs_only=False)
    print("files:", files)
    problems = []

    for i, n in Counter(q.get("id") for q in cases).items():
        if n > 1:
            problems.append(f"duplicate id {i}")
    for text, n in Counter(norm(q.get("question", "")) for q in cases).items():
        if n > 1:
            problems.append(f"duplicate question: {text[:70]!r}")
    for q in cases:
        problems += [f"{q.get('id', '?')}: {msg}" for msg in check_case(q)]

    # composition table: the Day 9 RECORD, generated, never hand-counted
    table = defaultdict(Counter)
    for q in cases:
        row = table[q.get("class", "?")]
        row[q.get("split", "?")] += 1
        row["verified"] += bool(q.get("verified"))
        row["hard"] += q.get("difficulty") == "hard"
    print(f"\n{'slice':14s} {'dev':>4s} {'test':>5s} {'total':>6s} {'hard':>5s} {'verified':>9s}")
    totals = Counter()
    for cls in CLASSES + sorted(set(table) - set(CLASSES)):
        if cls not in table:
            print(f"{cls:14s} {'-':>4s} {'-':>5s} {0:>6d}")
            continue
        r = table[cls]
        n = r["dev"] + r["test"]
        totals.update({"dev": r["dev"], "test": r["test"], "hard": r["hard"], "verified": r["verified"]})
        print(f"{cls:14s} {r['dev']:>4d} {r['test']:>5d} {n:>6d} {r['hard']:>5d} {r['verified']:>9d}")
    n = totals["dev"] + totals["test"]
    print(f"{'TOTAL':14s} {totals['dev']:>4d} {totals['test']:>5d} {n:>6d} {totals['hard']:>5d} {totals['verified']:>9d}")
    print("by behavior:", dict(Counter(q.get("expected_behavior") for q in cases)))
    print("by target:", dict(Counter(t for q in cases for t in q.get("targets", [])).most_common()))

    print(f"\n{len(cases)} cases")
    print("problems:" if problems else "no problems found")
    for msg in problems:
        print("  -", msg)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()