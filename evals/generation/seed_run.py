# evals/generation/seed_run.py
"""
Run the seed questions with the CORRECT pages as evidence.
This tests the prompt alone, assuming perfect search.

Run from the project root:
    PROMPT_VERSION=grounded_v2 python -m evals.generation.seed_run
"""

import json
from collections import defaultdict

from copilot.config import QUESTIONS_DIR
from copilot.generation.grounded import PROMPT_VERSION, ask, check, load_page

seeds = json.loads((QUESTIONS_DIR / "seed.json").read_text(encoding="utf-8"))
by_class = defaultdict(lambda: [0, 0])

for s in seeds:
    evidence = [load_page(d) for d in s["expected_docs"]]
    result, _ = ask(s["question"], evidence)
    problems = check(result, evidence)
    text = result["answer"].lower()
    missing = [w for w in s["must_include"] if w.lower() not in text]
    ok = result["status"] == "answered" and not problems and not missing
    by_class[s["class"]][0] += ok
    by_class[s["class"]][1] += 1
    if not ok:
        print(f"\n[FAIL] {s['id']} {s['question']}")
        print(f"  expected: {s['expected_answer']}")
        print(f"  got ({result['status']}): {result['answer'][:200]}")
        if problems or missing:
            print(f"  problems: {problems + [f'missing {w!r}' for w in missing]}")

print(f"\nprompt: {PROMPT_VERSION}")
for cls, (ok, n) in by_class.items():
    print(f"  {cls:12s} {ok}/{n}")