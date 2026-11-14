# evals/judge/judge.py
"""
Day 10, step 3: an LLM judge for three criteria, checked against human labels.

Each criterion is its own call with its own rubric (prompts/<criterion>_<version>.md):
    groundedness  reference-free: answer vs the evidence the copilot saw
    citation      reference-free: each [id] vs the block it points to
    correctness   reference-based: answer vs the golden case
N/A is decided by rules, not the model: empty answer -> groundedness and citation N/A;
no [id] in the answer -> citation N/A.

The judge is a different, stronger model than the copilot (JUDGE_MODEL), at temperature 0,
returning JSON. It quotes its support first and only then gives a verdict.

Run from the project root:
    python -m evals.judge.judge                     # judge all 45, compare with labels
    JUDGE_MODEL=gemini-3.5-pro python -m evals.judge.judge
    JUDGE_PROMPT=v2 python -m evals.judge.judge     # after you write prompts/*_v2.md
    python -m evals.judge.judge --models            # list models your key can use
Reads:
    data/invoicepilot/results/judge_answers.json    25 real answers (generate_answers.py)
    evals/judge/planted_answers.json                20 answers with a planted mistake
    evals/judge/labels.json                         the ground truth (Claude-drafted, human-reviewed)
Writes:
    data/invoicepilot/results/judge_<model>_<prompt>.json
"""

import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from copilot.config import RESULTS_DIR
from copilot.llm.client import API_KEY, call_model, user

HERE = Path(__file__).parent
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemini-3.5-flash")
JUDGE_PROMPT = os.getenv("JUDGE_PROMPT", "v3")          # v3 locked on Day 10
CRITERIA = ["groundedness", "citation", "correctness"]
PROMPT_FILE = {"groundedness": "grounded", "citation": "citation", "correctness": "correctness",
               "sufficiency": "sufficiency"}   # Day 11: the retrieval-layer question
WORKERS = int(os.getenv("JUDGE_WORKERS", "4"))

QUOTED = {  # what the judge must list before its verdict, per criterion
    "groundedness": ("claims", {"claim": {"type": "string"}, "quote": {"type": "string"}}),
    "citation": ("citations", {"sentence": {"type": "string"}, "id": {"type": "string"},
                               "quote": {"type": "string"}}),
    "correctness": ("core_facts", {"fact": {"type": "string"}, "quote": {"type": "string"}}),
    "sufficiency": ("needed_facts", {"fact": {"type": "string"}, "chunk_id": {"type": "string"},
                                     "quote": {"type": "string"}}),
}


def schema(criterion):
    key, item = QUOTED[criterion]
    props = {key: {"type": "array", "items": {"type": "object", "properties": item,
                                               "required": list(item)}}}
    if criterion == "correctness":
        props["behavior_shown"] = {"type": "string", "enum": ["answer", "refuse", "flag_conflict",
                                                              "resist", "followed_injection"]}
    props["verdict"] = {"type": "string", "enum": ["pass", "fail"]}
    props["reason"] = {"type": "string"}
    return {"type": "object", "properties": props, "required": list(props)}   # verdict comes last


# ---------- load the 45 cases into one shape ----------

def load_cases():
    real = json.loads((RESULTS_DIR / "judge_answers.json").read_text(encoding="utf-8"))
    cases = [{
        "id": r["id"], "kind": "real", "class": r["class"], "question": r["question"],
        "golden": r["golden"], "status": r["result"]["status"], "answer": r["result"]["answer"],
        "evidence": [{"id": e["id"], "text": e["text"]} for e in r["evidence"]],
    } for r in real]
    for p in json.loads((HERE / "planted_answers.json").read_text(encoding="utf-8")):
        cases.append({
            "id": p["id"], "kind": "planted", "class": p["cls"], "question": p["q"],
            "golden": {"expected_behavior": p["beh"], "expected_answer": p["exp"],
                       "must_include": p["must"], "injected": p["inj"]},
            "status": p["status"], "answer": p["ans"],
            "evidence": [{"id": e["id"], "text": e["t"]} for e in p["ev"]],
        })
    return cases


# ---------- build each criterion's input ----------

def evidence_text(case):
    return "\n\n".join(f'<evidence id="{e["id"]}">\n{e["text"]}\n</evidence>' for e in case["evidence"])


def judge_input(criterion, case):
    if criterion == "sufficiency":                       # retrieval: chunks vs golden, no answer at all
        g = case["golden"]
        return (f"QUESTION: {case['question']}\nGOLDEN ANSWER: {g['expected_answer']}\n"
                f"MUST_INCLUDE: {g.get('must_include') or []}\n\nCHUNKS:\n{evidence_text(case)}")
    answer = f"<answer status=\"{case['status']}\">\n{case['answer']}\n</answer>"
    if criterion in ("groundedness", "citation"):        # no golden answer: judge only what was shown
        # v3+: the judge also sees the question, so it can tell "the user said X" apart from a made-up X.
        question = f"QUESTION (written by the user):\n{case['question']}\n\n" if JUDGE_PROMPT not in ("v1", "v2") else ""
        return f"{question}EVIDENCE:\n{evidence_text(case)}\n\nANSWER:\n{answer}"
    g = case["golden"]
    gold = (f"QUESTION: {case['question']}\n"
            + (f"INJECTED: {g['injected']}\n" if g.get("injected") else "")
            + f"EXPECTED BEHAVIOR: {g['expected_behavior']}\n"
            f"GOLDEN ANSWER: {g['expected_answer']}\n"
            f"MUST_INCLUDE: {g.get('must_include') or []}")
    return f"{gold}\n\nASSISTANT ANSWER:\n{answer}"


def rule_na(criterion, case):
    """N/A is a fact about the answer, not a judgment. Decide it with code."""
    if criterion == "sufficiency":
        return case["golden"]["expected_behavior"] == "refuse"     # nothing to retrieve
    if criterion in ("groundedness", "citation") and not case["answer"].strip():
        return True
    if criterion == "citation" and not re.search(r"\[[^\]\s][^\]]*\]", case["answer"]):
        return True
    return False


def judge_one(criterion, case, version=None):
    if rule_na(criterion, case):
        return {"verdict": "na", "reason": "rule: nothing to check", "tokens": 0}
    system = (HERE / "prompts" / f"{PROMPT_FILE[criterion]}_{version or JUDGE_PROMPT}.md").read_text(encoding="utf-8")
    for max_tokens in (4000, 12000):     # thinking can run long on a messy answer: one retry with more room
        data = call_model([user(judge_input(criterion, case))], system=system, temperature=0,
                          max_tokens=max_tokens, model=JUDGE_MODEL,
                          extra_config={"responseMimeType": "application/json",
                                        "responseJsonSchema": schema(criterion)})
        cand = data["candidates"][0]
        if cand.get("finishReason") != "MAX_TOKENS":
            break
    if cand.get("finishReason") != "STOP":
        return {"verdict": "error", "reason": f"finishReason={cand.get('finishReason')}", "tokens": 0}
    out = json.loads("".join(p.get("text", "") for p in cand["content"]["parts"]))
    u = data.get("usageMetadata", {})
    out["tokens"] = u.get("promptTokenCount", 0) + u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
    return out


# ---------- agreement ----------

def kappa(pairs):
    """Cohen's kappa: agreement beyond what two raters would reach by chance."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] / n * cb[k] / n for k in set(ca) | set(cb))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def report(rows, labels):
    print(f"\nJudge {JUDGE_MODEL}, prompt {JUDGE_PROMPT}. Labels: Claude-drafted, human-reviewed.\n")
    print(f"{'criterion':13s} {'set':8s} {'n':>3s} {'agree':>6s} {'kappa':>6s} {'fails caught':>13s} {'false fails':>12s}")
    for c in CRITERIA:
        for kind in ("all", "real", "planted"):
            pairs = [(labels[r["id"]][c], r[c]["verdict"]) for r in rows
                     if (kind == "all" or r["kind"] == kind) and labels[r["id"]][c] != "na"]
            if not pairs:
                continue
            agree = sum(a == b for a, b in pairs) / len(pairs)
            fails = [b for a, b in pairs if a == "fail"]
            caught = f"{fails.count('fail')}/{len(fails)}"
            false_fail = sum(a == "pass" and b == "fail" for a, b in pairs)
            print(f"{c:13s} {kind:8s} {len(pairs):3d} {agree:6.0%} {kappa(pairs):6.2f} {caught:>13s} {false_fail:12d}")
        print()

    print("Confusion (rows = human, columns = judge), all 45:")
    for c in CRITERIA:
        m = Counter((labels[r["id"]][c], r[c]["verdict"]) for r in rows)
        vals = ["pass", "fail", "na"]
        print(f"  {c:13s}     " + "  ".join(f"{v:>5s}" for v in vals))
        for h in vals:
            if any(m[(h, j)] for j in vals + ["error"]):
                print(f"  {'':13s}{h:>5s}" + "  ".join(f"{m[(h, j)]:5d}" for j in vals))
    print("\nDisagreements:")
    for r in rows:
        for c in CRITERIA:
            h, j = labels[r["id"]][c], r[c]["verdict"]
            if h != j:
                print(f"  {r['id']:6s} {c:13s} human={h:4s} judge={j:5s}  {r[c].get('reason', '')[:110]}")


def list_models():
    resp = requests.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                        headers={"x-goog-api-key": API_KEY}, timeout=30)
    for m in resp.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            print(m["name"].removeprefix("models/"))


def main():
    if "--models" in sys.argv:
        return list_models()
    labels = json.loads((HERE / "labels.json").read_text(encoding="utf-8"))
    cases = load_cases()
    assert {c["id"] for c in cases} == set(labels), "cases and labels do not match"

    jobs = [(c, case) for case in cases for c in CRITERIA]
    print(f"judging {len(cases)} cases x {len(CRITERIA)} criteria with {JUDGE_MODEL} ...")
    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(lambda j: judge_one(*j), jobs))

    rows = [{"id": case["id"], "kind": case["kind"], "class": case["class"]} for case in cases]
    by_id = {r["id"]: r for r in rows}
    for (c, case), res in zip(jobs, results):
        by_id[case["id"]][c] = res
    errors = [(r["id"], c) for r in rows for c in CRITERIA if r[c]["verdict"] == "error"]
    if errors:
        print("judge errors:", errors)

    report(rows, labels)
    tokens = sum(res.get("tokens", 0) for res in results)
    out = RESULTS_DIR / f"judge_{JUDGE_MODEL}_{JUDGE_PROMPT}.json"
    out.write_text(json.dumps({"model": JUDGE_MODEL, "prompt": JUDGE_PROMPT, "tokens": tokens,
                               "rows": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{tokens:,} judge tokens. wrote {out}")


if __name__ == "__main__":
    main()
