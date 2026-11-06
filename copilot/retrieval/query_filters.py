# copilot/retrieval/query_filters.py
"""
Day 6, Lesson 2: pull version/plan filters out of a question.
Two methods: rules (regex) and self-query (LLM with a schema). Measured on tricky cases.

Run from the project root:
    python -m copilot.retrieval.query_filters
"""

import json
import re

from copilot.config import QUESTIONS_DIR
from copilot.llm.client import call_model, user

VERSIONS = ["2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.3.1"]
PLANS = ["Starter", "Professional", "Enterprise"]


# ------------------------------------------------------------------- rules
def rule_filters(question):
    v = re.search(r"\b2\.\d\.\d\b", question)
    p = re.search(r"\b(Starter|Professional|Enterprise)\b", question, re.IGNORECASE)
    return {
        "version": v.group(0) if v and v.group(0) in VERSIONS else "none",
        "plan": p.group(1).capitalize() if p else "none",
    }


# -------------------------------------------------------------- self-query
SELF_QUERY_SYSTEM = """You extract search filters from a sales engineer's question about InvoicePilot.

Versions (number, codename, release date):
2.0.0 Nova 2025-06-10 | 2.1.0 Solstice 2025-09-16 | 2.2.0 Meridian 2026-01-20 |
2.3.0 Aurora 2026-05-11 | 2.3.1 Aurora Patch 1 2026-08-14 (the latest version)

Plans: Starter, Professional (also called Pro), Enterprise.

Rules:
- Set version only if the question is clearly about one specific InvoicePilot version
  (by number, short number like "2.2", codename, or "the latest"). Otherwise "none".
- Set plan only if the question is about a customer on a specific InvoicePilot plan.
  Words used as ordinary adjectives ("enterprise-grade", "a starter template") are not plans.
- When unsure, choose "none". A wrong filter is worse than no filter."""

SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string", "enum": VERSIONS + ["none"]},
        "plan": {"type": "string", "enum": PLANS + ["none"]},
    },
    "required": ["version", "plan"],
}


def llm_filters(question):
    data = call_model(
        [user(question)], system=SELF_QUERY_SYSTEM, max_tokens=100,
        extra_config={"responseMimeType": "application/json", "responseJsonSchema": SCHEMA},
    )
    parts = data["candidates"][0]["content"]["parts"]
    return json.loads("".join(p.get("text", "") for p in parts))


# ------------------------------------------------- tricky cases, hand-labeled
TRICKY = [
    ("Does the Aurora release include a custom report builder?",        {"version": "2.3.0", "plan": "none"}),
    ("We're on the latest patch. Is the long-invoice PDF bug fixed?",   {"version": "2.3.1", "plan": "none"}),
    ("Did 2.2 have bulk invoice actions?",                              {"version": "2.2.0", "plan": "none"}),
    ("Can a Pro customer brand their client portal?",                   {"version": "none",  "plan": "Professional"}),
    ("Is there a starter template for invoices?",                       {"version": "none",  "plan": "none"}),
    ("Does InvoicePilot offer enterprise-grade security like SSO?",     {"version": "none",  "plan": "none"}),
    ("What does error IP-4090 mean?",                                   {"version": "none",  "plan": "none"}),
    ("Could a Starter customer on 2.2.0 send bulk reminders?",          {"version": "2.2.0", "plan": "Starter"}),
]


if __name__ == "__main__":
    print("===== Tricky cases (hand-labeled) =====")
    score = {"rules": 0, "llm": 0}
    for q, expected in TRICKY:
        r, l = rule_filters(q), llm_filters(q)
        score["rules"] += r == expected
        score["llm"] += l == expected
        print(f"\nQ: {q}\n   expected {expected}")
        print(f"   rules    {r} {'OK' if r == expected else 'WRONG'}")
        print(f"   llm      {l} {'OK' if l == expected else 'WRONG'}")
    print(f"\nexact match: rules {score['rules']}/{len(TRICKY)}, llm {score['llm']}/{len(TRICKY)}")

    print("\n===== Your seed + hard questions: where do the two methods disagree? =====")
    questions = (json.loads((QUESTIONS_DIR / "seed.json").read_text())
                 + json.loads((QUESTIONS_DIR / "hard.json").read_text()))
    found = 0
    for s in questions:
        r, l = rule_filters(s["question"]), llm_filters(s["question"])
        if r != l:
            print(f"{s['id']:6s} rules {r}  llm {l}  | {s['question'][:60]}")
        if l != {"version": "none", "plan": "none"}:
            found += 1
    print(f"\nquestions where the LLM found a filter: {found}/{len(questions)}")