# src2/day2_decompose.py
"""
Day 2, Lesson 5: decomposition. Split the question, answer each part with the
grounded prompt, combine in plain code. Tested on ALL attacks, not just the one it fixes.

Run from src2/:
    RUNS=5 PROMPT_VERSION=grounded_v2 python day2_decompose.py
"""

import json
import os

from day1_first_call import call_model, user
from day2_attacks import ATTACKS, judge
from day2_grounded import PROMPT_VERSION, ask, check

SPLIT_SYSTEM = (
    "Split the user's question into the smallest set of independent sub-questions. "
    "Do not answer anything. If it is already a single question, return it unchanged as the only item. "
    "Make each sub-question self-contained: replace words like 'ours', 'we' or 'our product' with "
    "'InvoicePilot'. Keep any claim or assumption the user states, inside the sub-question it belongs to."
)

SPLIT_SCHEMA = {
    "type": "object",
    "properties": {"parts": {"type": "array", "items": {"type": "string"}}},
    "required": ["parts"],
}


def split(question):
    data = call_model(
        [user(question)], system=SPLIT_SYSTEM, max_tokens=300,
        extra_config={"responseMimeType": "application/json", "responseJsonSchema": SPLIT_SCHEMA},
    )
    cand = data["candidates"][0]
    parts = json.loads("".join(p.get("text", "") for p in cand["content"]["parts"]))["parts"]
    return parts or [question], data.get("usageMetadata", {})


def combine(results):
    """Plain code, no model: status from the parts, answers and gaps joined."""
    statuses = {r["status"] for r in results}
    if statuses == {"answered"}:
        status = "answered"
    elif statuses == {"not_in_documentation"}:
        status = "not_in_documentation"
    else:
        status = "partial"
    citations = sorted({c for r in results for c in r["citations"]})
    answer = " ".join(r["answer"] for r in results if r["answer"])
    not_covered = "; ".join(r["not_covered"] for r in results if r["not_covered"])
    return {"status": status, "citations": citations, "answer": answer, "not_covered": not_covered}


def answer_decomposed(question, evidence):
    parts, split_usage = split(question)
    results, tokens_in, tokens_out = [], split_usage.get("promptTokenCount", 0), split_usage.get("candidatesTokenCount", 0)
    for p in parts:
        r, usage = ask(p, evidence)
        results.append(r)
        tokens_in += usage.get("promptTokenCount", 0)
        tokens_out += usage.get("candidatesTokenCount", 0)
    return combine(results), parts, 1 + len(parts), tokens_in, tokens_out


if __name__ == "__main__":
    RUNS = int(os.getenv("RUNS", "3"))
    print(f"DECOMPOSED | prompt version: {PROMPT_VERSION} | runs per attack: {RUNS}")

    total_pass = total = all_calls = all_in = 0
    for a in ATTACKS:
        passes, last_fail, last_parts = 0, None, None
        for _ in range(RUNS):
            result, parts, calls, t_in, _ = answer_decomposed(a["q"], a["evidence"])
            all_calls += calls
            all_in += t_in
            last_parts = parts
            fails = judge(a, result, check(result, a["evidence"]))
            if fails:
                last_fail = (result, fails)
            else:
                passes += 1
        total_pass += passes
        total += RUNS
        flag = "OK   " if passes == RUNS else ("FLAKY" if passes else "FAIL ")
        print(f"[{flag}] {passes}/{RUNS}  {a['name']}")
        print(f"         split into: {last_parts}")
        if last_fail:
            print(f"         example failure: {last_fail[1]}")
            print(f"         answer: {last_fail[0]['answer'][:160]!r}")

    print(f"\n{total_pass}/{total} runs passed (decomposed)")
    print(f"avg model calls per question: {all_calls / total:.1f}")
    print(f"avg input tokens per question: {all_in / total:.0f}")