# evals/scorecard.py
"""
Day 11: one full run, each layer graded on its own, every failure blamed on a layer.

For every dev case:
  1. retrieve (V4)                          -> quote recall      (free, strict lower bound)
  2. judge: are the chunks ENOUGH?          -> retrieval verdict (sufficiency_v1)
  3. answer (grounded_v2)
  4. deterministic checks                   -> evals/checks.py
  5. judge v3: grounded, citation, correct  -> generation verdict
  6. blame:
         chunks enough + answer correct  -> ok
         chunks enough + answer wrong    -> generation   (fix the prompt / model)
         chunks short  + answer wrong    -> retrieval    (fix retrieval first)
         chunks short  + answer correct  -> lucky        (judge disagreement, or a correct refusal)
     refusal cases have nothing to retrieve: ok or generation.

Run from the project root:
    python -m evals.scorecard                 # generate answers + judge  (~$0.10, a few minutes)
    python -m evals.scorecard --reuse         # reuse saved answers, judge again
    SPLIT=test python -m evals.scorecard      # ONLY at milestones (Days 15, 22, 30)
Writes:
    data/invoicepilot/results/run_<split>.json        answers + evidence (reused by --reuse)
    data/invoicepilot/results/scorecard_<split>.json  every verdict, check and box
"""

import json
import os
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from copilot.config import RESULTS_DIR
from evals.checks import run_checks
from evals.common import load_questions
from evals.judge.judge import JUDGE_MODEL, JUDGE_PROMPT, WORKERS, judge_one
from evals.retrieval.evidence_recall import norm

SPLIT = os.getenv("SPLIT", "dev")
SUFFICIENCY_PROMPT = os.getenv("SUFFICIENCY_PROMPT", "v1")
CRITERIA = ["sufficiency", "groundedness", "citation", "correctness"]
CLASSES = ["capability", "exact_token", "tier_gated", "temporal", "multi_hop", "synthesis",
           "conflict", "injection", "non_official", "out_of_scope"]
QUALITY_CHECKS = ["schema", "citations_resolve", "cited_facts", "edition_named"]


def generate(questions):
    from copilot.generation.answer_v4 import answer
    from copilot.retrieval.pipeline import Retriever
    r = Retriever()
    rows = []
    for i, q in enumerate(questions, 1):
        out = answer(q["question"], r)
        for e in out["evidence"]:
            e["plans"] = r.chunk.get(e["id"], {}).get("plans")
        rows.append({"id": q["id"], **out})
        print(f"  {i:3d}/{len(questions)} {q['id']:7s} {out['result']['status']}")
    r.close()
    return rows


def blame(behavior, enough, correct):
    if behavior == "refuse":
        return "ok" if correct else "generation"
    if enough and correct:
        return "ok"
    if enough:
        return "generation"
    return "lucky" if correct else "retrieval"


def pct(xs):
    xs = [x for x in xs if x is not None]
    return f"{sum(xs) / len(xs):.0%}" if xs else "-"


def main():
    questions, _ = load_questions(split=SPLIT, with_docs_only=False)
    run_file = RESULTS_DIR / f"run_{SPLIT}.json"
    if "--reuse" in sys.argv and run_file.exists():
        runs = json.loads(run_file.read_text(encoding="utf-8"))
        print(f"reusing {len(runs)} answers from {run_file.name}")
    else:
        print(f"answering {len(questions)} {SPLIT} cases with V4 + grounded_v2 ...")
        runs = generate(questions)
        run_file.write_text(json.dumps(runs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    run_by_id = {r["id"]: r for r in runs}

    cases = []
    for q in questions:
        r = run_by_id[q["id"]]
        cases.append({"id": q["id"], "question": q["question"], "status": r["result"]["status"],
                      "answer": r["result"]["answer"],
                      "evidence": [{"id": e["id"], "text": e["text"]} for e in r["evidence"]],
                      "golden": {k: q.get(k) for k in ("expected_behavior", "expected_answer",
                                                        "must_include", "injected")}})

    jobs = [(c, case) for case in cases for c in CRITERIA]
    print(f"judging {len(jobs)} verdicts with {JUDGE_MODEL} (sufficiency {SUFFICIENCY_PROMPT}, answers {JUDGE_PROMPT}) ...")
    with ThreadPoolExecutor(WORKERS) as pool:
        verdicts = list(pool.map(
            lambda j: judge_one(j[0], j[1], SUFFICIENCY_PROMPT if j[0] == "sufficiency" else None), jobs))
    judged = defaultdict(dict)
    for (c, case), v in zip(jobs, verdicts):
        judged[case["id"]][c] = v

    rows = []
    for q in questions:
        r, j = run_by_id[q["id"]], judged[q["id"]]
        texts = [norm(e["text"]) for e in r["evidence"]]
        quote_all = all(any(norm(e) in t for t in texts) for e in q["evidence"]) if q.get("evidence") else None
        ms = r["ms"]["retrieve"] + r["ms"]["llm"]
        checks = run_checks(r["result"], r["evidence"], q["question"], q["class"], ms, r["cost"])
        v = {c: j[c]["verdict"] for c in CRITERIA}
        ok = lambda c: None if v[c] in ("na", "error") else v[c] == "pass"
        rows.append({
            "id": q["id"], "class": q["class"], "behavior": q["expected_behavior"],
            "status": r["result"]["status"], "quote_all": quote_all, "verdicts": v,
            "reasons": {c: j[c].get("reason", "") for c in CRITERIA},
            "checks": {k: {"ok": a, "detail": b} for k, (a, b) in checks.items()},
            "box": blame(q["expected_behavior"], ok("sufficiency"), ok("correctness")),
            "ms": ms, "cost": r["cost"],
        })

    # ---------- the scorecard ----------
    print(f"\n## Scorecard: {SPLIT}, V4 + grounded_v2, judge {JUDGE_MODEL} {JUDGE_PROMPT}\n")
    print("| class | n | quotes found | chunks enough | correct | grounded | citations ok | checks ok "
          "| blame: retrieval | blame: generation | lucky |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for cls in CLASSES + ["ALL"]:
        rs = [x for x in rows if cls in ("ALL", x["class"])]
        if not rs:
            continue
        judge_ok = lambda c: [None if x["verdicts"][c] in ("na", "error") else x["verdicts"][c] == "pass" for x in rs]
        boxes = Counter(x["box"] for x in rs)
        checks_ok = [all(x["checks"][k]["ok"] for k in QUALITY_CHECKS) for x in rs]
        print(f"| {cls} | {len(rs)} | {pct([x['quote_all'] for x in rs])} | {pct(judge_ok('sufficiency'))} "
              f"| {pct(judge_ok('correctness'))} | {pct(judge_ok('groundedness'))} | {pct(judge_ok('citation'))} "
              f"| {pct(checks_ok)} | {boxes['retrieval']} | {boxes['generation']} | {boxes['lucky']} |")

    print("\nDeterministic checks (fails out of", len(rows), "):")
    for k in QUALITY_CHECKS + ["latency_budget", "cost_budget"]:
        bad = [x["id"] for x in rows if not x["checks"][k]["ok"]]
        print(f"  {k:18s} {len(bad):3d}  {', '.join(bad[:12])}")

    ms = np.array([x["ms"] for x in rows])
    print(f"\nlatency per answer: median {np.median(ms):.0f} ms, p95 {np.percentile(ms, 95):.0f} ms")
    print(f"answer cost: ${sum(x['cost'] for x in rows):.4f} total, ${np.mean([x['cost'] for x in rows]):.5f} each")
    errors = [(x["id"], c) for x in rows for c in CRITERIA if x["verdicts"][c] == "error"]
    if errors:
        print("judge errors:", errors)

    print("\nEvery failure, by layer:")
    for box in ("retrieval", "generation", "lucky"):
        for x in rows:
            if x["box"] == box:
                c = "sufficiency" if box == "retrieval" else "correctness"
                print(f"  {box:10s} {x['id']:7s} {x['class']:13s} {x['reasons'][c][:100]}")

    out = RESULTS_DIR / f"scorecard_{SPLIT}.json"
    out.write_text(json.dumps({"split": SPLIT, "judge": JUDGE_MODEL, "judge_prompt": JUDGE_PROMPT,
                               "sufficiency_prompt": SUFFICIENCY_PROMPT, "rows": rows},
                              indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
