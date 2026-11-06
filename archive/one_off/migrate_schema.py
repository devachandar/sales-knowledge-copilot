# evals/migrate_schema.py
"""
Day 9, one-off: move the 68 existing questions to the golden-set format.

Adds to every case:
  expected_behavior  "answer" (all 68 are answerable questions)
  evidence           1 exact quote from an expected doc that contains the core fact
  targets            failure categories from the taxonomy (by class, plus hand overrides)
  split              "dev" (these 68 were tuned on all week, so none of them can be test)
  verified           false (you flip it after checking the case yourself)
The old free-text "targets" note is kept as "notes".

Run from the project root, then review with `git diff evals/questions/`:
    python -m evals.migrate_schema
"""

import json
import re

from copilot.config import DOCUMENTS_FILE, QUESTIONS_DIR
from evals.common import QUESTION_SETS

DOCS = {json.loads(l)["doc_id"]: json.loads(l)["text"]
        for l in open(DOCUMENTS_FILE, encoding="utf-8")}

TARGETS_BY_CLASS = {
    "capability": ["meaning_match"],
    "exact_token": ["lookalike_token"],
    "tier_gated": ["plan_gating"],
    "temporal": ["version_competition"],
    "non_official": ["authority_override"],
}
# Extra tags for cases we know target a specific failure (from failures.md and Days 5-8).
EXTRA = {
    "h-04": ["chunk_context"], "h-05": ["chunk_context"], "h-06": ["chunk_context", "incomplete_answer"],
    "h-10": ["vocabulary_mismatch"], "h-11": ["vocabulary_mismatch"], "h-12": ["vocabulary_mismatch"],
    "h-13": ["vocabulary_mismatch"], "h-14": ["low_authority_source"], "h-15": ["chunk_context"],
    "c1-07": ["lookalike_fact"], "c1-08": ["chunk_context"],
    "f-01": ["plan_filter_removes_evidence"], "f-02": ["plan_filter_removes_evidence"],
    "f-07": ["low_authority_source"], "h-07": ["version_filter_removes_evidence"],
    "h-08": ["version_filter_removes_evidence"], "c4-03": ["version_filter_removes_evidence"],
    "e-02": ["low_authority_source"], "e-07": ["low_authority_source"],
}
STOP = set("a an and are as at be by can do does for from has have how i if in is it its of on or our "
           "so that the their them they this to was we what when which who why will with you your".split())


def find_evidence(q):
    """The line in an expected doc that has the core fact and shares the most words with the question."""
    words = {w for w in re.findall(r"[a-z0-9][a-z0-9\-.]+", q["question"].lower()) if w not in STOP}
    core = [m.lower() for m in q["must_include"]]
    best = None
    for doc_id in q["expected_docs"]:
        for line in DOCS.get(doc_id, "").splitlines():
            line = line.strip()
            low = line.lower()
            if not line or line.startswith(("#", "|---", "| ---")) or not all(c in low for c in core):
                continue                      # headings and table separators are not evidence
            if not re.sub(r"[|\s]|starter|professional|enterprise", "", low):
                continue                      # a table header row of plan names only
            overlap = sum(w in low for w in words)
            key = (overlap, -len(line))
            if best is None or key > best[0]:
                best = (key, line, doc_id)
    return best


def main():
    missing = []
    for name, filename in QUESTION_SETS.items():
        path = QUESTIONS_DIR / filename
        cases = json.loads(path.read_text(encoding="utf-8"))
        out = []
        for q in cases:
            if "expected_behavior" in q:            # already migrated: leave it alone
                out.append(q)
                continue
            found = find_evidence(q)
            if found is None:
                missing.append(q["id"])
            note = q.pop("targets", None) or q.pop("filter_test", None) or q.pop("notes", None)
            q.pop("filter_test", None)
            new = {
                "id": q["id"], "class": q["class"], "question": q["question"],
                "expected_behavior": "answer",
                "expected_answer": q["expected_answer"],
                "expected_docs": q["expected_docs"],
                "evidence": [found[1]] if found else [],
                "must_include": q["must_include"],
                "difficulty": q["difficulty"],
                "targets": TARGETS_BY_CLASS[q["class"]] + EXTRA.get(q["id"], []),
                "split": "dev",
                "verified": False,
            }
            extra_notes = [n for n in (note, q.get("notes")) if n]
            if extra_notes:
                new["notes"] = " | ".join(dict.fromkeys(extra_notes))
            out.append(new)
            if found:
                print(f"{q['id']:6s} {found[2]:45s} {found[1][:90]}")
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nmigrated {sum(len(json.loads((QUESTIONS_DIR / f).read_text())) for f in QUESTION_SETS.values())} cases")
    print("no evidence line found:", missing or "none")


if __name__ == "__main__":
    main()