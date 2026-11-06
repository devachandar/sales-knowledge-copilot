# evals/common.py
"""
Shared helpers for every eval script.

Which questions (QUESTIONS), by short name or path:
    QUESTIONS=seed,hard python -m evals.retrieval.run_pipeline
With no QUESTIONS set, every set is used.

Which split (SPLIT): dev (default), test, or all.
    The test split is SEALED: run it only at milestones (Days 15, 22, 30), never while tuning.
    SPLIT=test python -m evals.retrieval.run_pipeline

Retrieval evals only score cases that have expected documents (refusals and some
injection cases have none); the question checker loads everything.
"""

import json
import os
from pathlib import Path

from copilot.config import QUESTIONS_DIR

QUESTION_SETS = {
    "seed": "seed.json",
    "hard": "hard.json",
    "filter": "filter.json",
    "exact": "exact.json",
    "non_official": "non_official.json",
    "core_v2": "core_v2.json",            # Day 9: more cases for classes 1-4 and non_official
    "multi_hop": "multi_hop.json",
    "synthesis": "synthesis.json",
    "out_of_scope": "out_of_scope.json",
    "conflict": "conflict.json",
    "injection": "injection.json",
}
ALL_SETS = ",".join(QUESTION_SETS)
WEEK1_SETS = "seed,hard,filter,exact,non_official"   # the 68 behind the Day 8 results table


def load_questions(names=None, split=None, with_docs_only=True):
    """Return (questions, files).

    names           overrides the QUESTIONS env var
    split           "dev" | "test" | "all"; overrides the SPLIT env var (default "dev")
    with_docs_only  drop cases with no expected_docs (they cannot be scored on retrieval)
    """
    names = names or os.getenv("QUESTIONS", ALL_SETS)
    split = split or os.getenv("SPLIT", "dev")
    if split not in ("dev", "test", "all"):
        raise SystemExit(f"SPLIT must be dev, test, or all (got {split!r})")
    files = []
    for name in (n.strip() for n in names.split(",") if n.strip()):
        path = QUESTIONS_DIR / QUESTION_SETS[name] if name in QUESTION_SETS else Path(name)
        if not path.exists():
            raise SystemExit(f"question set not found: {name} (known: {ALL_SETS})")
        files.append(path)
    questions = [q for f in files for q in json.loads(f.read_text(encoding="utf-8"))]
    if split != "all":
        questions = [q for q in questions if q.get("split", "dev") == split]
    if with_docs_only:
        questions = [q for q in questions if q.get("expected_docs")]
    return questions, [f.name for f in files]
