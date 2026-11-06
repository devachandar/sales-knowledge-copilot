# evals/common.py
"""
Shared helpers for every eval script.

QUESTIONS picks the question sets, by short name or by path:
    QUESTIONS=seed,hard python -m evals.retrieval.run_pipeline
    QUESTIONS=evals/questions/exact.json python -m evals.retrieval.bm25_eval
With no QUESTIONS set, every set is used.
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
}
ALL_SETS = ",".join(QUESTION_SETS)


def load_questions(names=None):
    """Return (questions, files). `names` overrides the QUESTIONS env var."""
    names = names or os.getenv("QUESTIONS", ALL_SETS)
    files = []
    for name in (n.strip() for n in names.split(",") if n.strip()):
        path = QUESTIONS_DIR / QUESTION_SETS[name] if name in QUESTION_SETS else Path(name)
        if not path.exists():
            raise SystemExit(f"question set not found: {name} (known: {ALL_SETS})")
        files.append(path)
    questions = [q for f in files for q in json.loads(f.read_text(encoding="utf-8"))]
    return questions, [f.name for f in files]
