# evals/ci.py
"""
Day 12: one command that runs the generation eval and diffs it against the last accepted run.

Retrieval is FROZEN: the top-5 chunks for every dev question are saved once in
evals/baselines/retrieval_dev.json, together with the judge's sufficiency verdict. A prompt
change cannot change retrieval, so CI only reruns generation + checks + judge on those chunks.
That needs no Postgres, no BM25 index and no reranker: just Python, requests and an API key.

    python -m evals.ci freeze                  # (Mac) freeze retrieval from run_dev.json + scorecard_dev.json
    python -m evals.ci run --label noise_a     # one run, saved to results/ci_<label>.json
    python -m evals.ci compare noise_a noise_b # diff two saved runs (markdown)
    python -m evals.ci                         # run + diff vs evals/baselines/dev.json; exit 1 on regression
    python -m evals.ci --save-baseline         # run, then make it the new baseline

Env: PROMPT_VERSION (grounded_v2), JUDGE_MODEL, JUDGE_PROMPT (v3), CI_MAX_DROP (points), CI_WORKERS.
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from copilot.config import RESULTS_DIR
from evals.checks import run_checks
from evals.common import load_questions

HERE = Path(__file__).parent
BASELINES = HERE / "baselines"
FROZEN = BASELINES / "retrieval_dev.json"
BASELINE = BASELINES / "dev.json"
CRITERIA = ["groundedness", "citation", "correctness"]
QUALITY_CHECKS = ["schema", "citations_resolve", "cited_facts", "edition_named"]
CLASSES = ["capability", "exact_token", "tier_gated", "temporal", "multi_hop", "synthesis",
           "conflict", "injection", "non_official", "out_of_scope"]
MAX_DROP = float(os.getenv("CI_MAX_DROP", "3"))     # points; set from the measured noise floor
WORKERS = int(os.getenv("CI_WORKERS", "6"))


# ---------- freeze retrieval (run on the Mac, where Postgres and the reranker live) ----------

def freeze():
    runs = json.loads((RESULTS_DIR / "run_dev.json").read_text(encoding="utf-8"))
    card = {r["id"]: r for r in json.loads((RESULTS_DIR / "scorecard_dev.json").read_text())["rows"]}
    frozen = {r["id"]: {"evidence": r["evidence"],
                        "sufficiency": card[r["id"]]["verdicts"]["sufficiency"],
                        "retrieval_config": r["config"]["retrieval"]} for r in runs}
    BASELINES.mkdir(exist_ok=True)
    FROZEN.write_text(json.dumps(frozen, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"froze retrieval for {len(frozen)} questions -> {FROZEN}")


# ---------- one run ----------

def run(label):
    from copilot.generation.grounded import PROMPT_VERSION, ask
    from copilot.llm.client import MODEL
    from evals.judge.judge import JUDGE_MODEL, JUDGE_PROMPT, judge_one

    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    questions, _ = load_questions(split="dev", with_docs_only=False)

    def answer_one(q):
        ev = frozen[q["id"]]["evidence"]
        result, usage = ask(q["question"], [{"id": e["id"], "text": e["text"]} for e in ev])
        tin = usage.get("promptTokenCount", 0)
        tout = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
        return result, tin / 1e6 * 0.30 + tout / 1e6 * 2.50

    print(f"[{label}] answering {len(questions)} dev cases: {PROMPT_VERSION} on {MODEL}, frozen retrieval ...")
    with ThreadPoolExecutor(WORKERS) as pool:
        answers = list(pool.map(answer_one, questions))

    cases = [{"id": q["id"], "question": q["question"], "status": res["status"], "answer": res["answer"],
              "evidence": [{"id": e["id"], "text": e["text"]} for e in frozen[q["id"]]["evidence"]],
              "golden": {k: q.get(k) for k in ("expected_behavior", "expected_answer", "must_include", "injected")}}
             for q, (res, _) in zip(questions, answers)]
    jobs = [(c, case) for case in cases for c in CRITERIA]
    print(f"[{label}] judging {len(jobs)} verdicts with {JUDGE_MODEL} {JUDGE_PROMPT} ...")
    with ThreadPoolExecutor(WORKERS) as pool:
        verdicts = list(pool.map(lambda j: judge_one(*j), jobs))
    judged = defaultdict(dict)
    for (c, case), v in zip(jobs, verdicts):
        judged[case["id"]][c] = v

    rows = {}
    for q, (res, cost) in zip(questions, answers):
        ev = frozen[q["id"]]["evidence"]
        checks = run_checks(res, ev, q["question"], q["class"], 0, cost)
        rows[q["id"]] = {
            "class": q["class"], "status": res["status"], "answer": res["answer"],
            "sufficiency": frozen[q["id"]]["sufficiency"],
            "verdicts": {c: judged[q["id"]][c]["verdict"] for c in CRITERIA},
            "reasons": {c: judged[q["id"]][c].get("reason", "") for c in CRITERIA},
            "checks_ok": all(checks[k][0] for k in QUALITY_CHECKS),
            "failed_checks": [k for k in QUALITY_CHECKS if not checks[k][0]],
            "cost": cost,
        }
    out = {"label": label, "when": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "config": {"prompt": PROMPT_VERSION, "model": MODEL, "judge": JUDGE_MODEL,
                      "judge_prompt": JUDGE_PROMPT, "retrieval": "frozen V4"},
           "summary": summarize(rows), "rows": rows}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"ci_{label}.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[{label}] correctness {out['summary']['ALL']['correctness']:.0%}  ->  {path}")
    return out


def summarize(rows):
    def rate(rs, key):
        vals = [r["verdicts"][key] for r in rs if r["verdicts"][key] in ("pass", "fail")]
        return sum(v == "pass" for v in vals) / len(vals) if vals else None
    out = {}
    for cls in CLASSES + ["ALL"]:
        rs = [r for r in rows.values() if cls in ("ALL", r["class"])]
        if rs:
            out[cls] = {"n": len(rs), **{c: rate(rs, c) for c in CRITERIA},
                        "checks": sum(r["checks_ok"] for r in rs) / len(rs)}
    return out


# ---------- compare two runs ----------

def fmt(x):
    return "-" if x is None else f"{x:.0%}"


def delta(a, b):
    if a is None or b is None:
        return ""
    d = round((b - a) * 100)
    return "±0" if d == 0 else f"{d:+d}"


def compare(base, new):
    """Return (markdown, regressed)."""
    sa, sb = base["summary"], new["summary"]
    drop = (sa["ALL"]["correctness"] - sb["ALL"]["correctness"]) * 100
    regressed = drop > MAX_DROP
    fixed, broke, flips = [], [], Counter()
    for cid, rb in new["rows"].items():
        ra = base["rows"].get(cid)
        if not ra:
            continue
        for c in CRITERIA:
            if ra["verdicts"][c] != rb["verdicts"][c]:
                flips[c] += 1
        a, b = ra["verdicts"]["correctness"], rb["verdicts"]["correctness"]
        if a == "fail" and b == "pass":
            fixed.append(cid)
        elif a == "pass" and b == "fail":
            broke.append(cid)

    ca, cb = base["config"], new["config"]
    changed = [f"{k}: `{ca.get(k)}` → `{cb.get(k)}`" for k in cb if ca.get(k) != cb.get(k)]
    verdict = (f"❌ **Regression**: correctness dropped {drop:.0f} points (limit {MAX_DROP:.0f})" if regressed
               else f"✅ **No regression** (correctness change {-drop:+.0f} points, limit −{MAX_DROP:.0f})")
    lines = [f"## Eval delta: `{base['label']}` → `{new['label']}`", "", verdict, "",
             "Changed: " + ("; ".join(changed) if changed else "nothing in config (noise check)"), "",
             "| | correct | grounded | citations ok | checks ok |", "|---|---|---|---|---|"]
    for cls in ["ALL"] + CLASSES:
        if cls in sb:
            a, b = sa.get(cls, {}), sb[cls]
            cells = " | ".join(f"{fmt(a.get(k))} → {fmt(b[k])} {delta(a.get(k), b[k])}"
                               for k in ("correctness", "groundedness", "citation", "checks"))
            name = f"**{cls}**" if cls == "ALL" else cls
            lines.append(f"| {name} (n={b['n']}) | {cells} |")
    lines += ["", f"**Fixed ({len(fixed)}):** {', '.join(fixed) or 'none'}  ",
              f"**Broke ({len(broke)}):** {', '.join(broke) or 'none'}  ",
              f"Verdict flips: " + ", ".join(f"{c} {flips[c]}" for c in CRITERIA)]
    for cid in broke:
        lines.append(f"- `{cid}` now fails: {new['rows'][cid]['reasons']['correctness'][:160]}")
    cost = sum(r["cost"] for r in new["rows"].values())
    lines += ["", f"<sub>{cb['prompt']} on {cb['model']} · judge {cb['judge']} {cb['judge_prompt']} · "
                  f"retrieval {cb['retrieval']} · answer cost ${cost:.3f}</sub>"]
    return "\n".join(lines), regressed


def load_run(name):
    p = Path(name)
    if not p.exists():
        p = RESULTS_DIR / f"ci_{name}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="check", choices=["check", "freeze", "run", "compare"])
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--label", default=os.getenv("CI_LABEL", "current"))
    ap.add_argument("--save-baseline", action="store_true")
    ap.add_argument("--report", default=os.getenv("CI_REPORT", "eval_report.md"))
    a = ap.parse_args()

    if a.cmd == "freeze":
        return freeze()
    if a.cmd == "run":
        return run(a.label)
    if a.cmd == "compare":
        md, _ = compare(load_run(a.runs[0]), load_run(a.runs[1]))
        return print(md)

    new = run(a.label)
    if a.save_baseline or not BASELINE.exists():
        BASELINE.write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"saved as baseline -> {BASELINE}")
        return
    md, regressed = compare(json.loads(BASELINE.read_text(encoding="utf-8")), new)
    Path(a.report).write_text(md + "\n", encoding="utf-8")
    print("\n" + md)
    sys.exit(1 if regressed else 0)


if __name__ == "__main__":
    main()
