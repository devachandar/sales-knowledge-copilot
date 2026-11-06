# archive/learning/day1_structured.py
"""
Day 1, Lesson 4: structured output. Make the model return JSON your code can trust,
then check the parts the schema can't check.

Run from src2/:
    python day1_structured.py
"""

import json

from day1_first_call import call_model, user

# Two small "retrieved chunks", copied from the real help center.
# On Day 4, retrieval will pick these for you. Today we hand-pick them.
EVIDENCE = [
    {"id": "auto-match#1",
     "text": "Added in 2.3.0. Auto-match compares incoming bank transactions with recorded "
             "invoices and expenses and suggests matches. Amount must match exactly. "
             "Date must be within 5 days."},
    {"id": "auto-match#2",
     "text": "Known issue: On 2.3.1, auto-match does not convert foreign-currency amounts "
             "(BUG-2310-01, Critical). Use manual matching for foreign-currency transactions "
             "until a fix ships."},
]

SYSTEM = (
    "You answer questions for sales engineers using ONLY the evidence provided. "
    "If the evidence does not contain the answer, set status to not_in_documentation. "
    "Never use outside knowledge."
)

# The schema. Notice the order: status first, then citations, then the answer.
SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["answered", "not_in_documentation"],
            "description": "not_in_documentation if the evidence does not answer the question",
        },
        "citations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "ids of the evidence chunks the answer is based on",
        },
        "answer": {
            "type": "string",
            "description": "the answer, only from the cited evidence; empty if not answered",
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["status", "citations", "answer", "confidence"],
}

QUESTIONS = [
    "In which version was auto-match added?",                        # answerable
    "Does auto-match work for EUR transactions on 2.3.1?",           # answerable, needs chunk 2
    "When will BUG-2310-01 be fixed?",                               # NOT in the evidence
]


def build_prompt(question):
    # Evidence goes in the user turn, clearly marked, separate from our rules
    chunks = "\n".join(f"[{c['id']}] {c['text']}" for c in EVIDENCE)
    return f"EVIDENCE:\n{chunks}\n\nQUESTION: {question}"


def get_text(data):
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def check_meaning(result):
    """The checks the schema CANNOT do for us."""
    problems = []
    valid_ids = {c["id"] for c in EVIDENCE}
    for cid in result["citations"]:
        if cid not in valid_ids:
            problems.append(f"cites a chunk we never sent: {cid}")
    if result["status"] == "answered" and not result["citations"]:
        problems.append("answered without citing anything")
    if result["status"] == "not_in_documentation" and result["answer"].strip():
        problems.append("says not_in_documentation but still gave an answer")
    return problems


if __name__ == "__main__":
    # --- Part A: just ASK for JSON in the prompt, no schema ------------------
    print("\n===== A: asking nicely for JSON (no schema) =====")
    data = call_model(
        [user(build_prompt(QUESTIONS[0]) + "\n\nReply in JSON with fields status, citations, answer.")],
        system=SYSTEM,
    )
    raw = get_text(data)
    print("RAW TEXT:", repr(raw))
    try:
        print("parsed OK:", json.loads(raw))
    except json.JSONDecodeError as e:
        print("json.loads FAILED:", e)

    # --- Part B: schema-enforced ---------------------------------------------
    print("\n===== B: schema-enforced =====")
    for q in QUESTIONS:
        data = call_model(
            [user(build_prompt(q))],
            system=SYSTEM,
            extra_config={
                "responseMimeType": "application/json",
                "responseJsonSchema": SCHEMA,
            },
        )
        result = json.loads(get_text(data))           # shape is guaranteed
        problems = check_meaning(result)               # meaning is NOT
        print(f"\nQ: {q}")
        print(json.dumps(result, indent=2))
        print("meaning check:", "OK" if not problems else problems)