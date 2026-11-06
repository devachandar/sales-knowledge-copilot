# archive/learning/day1_tools.py
"""
Day 1, Lesson 5: a tool-calling loop written by hand.
The model ASKS for tools. Our code RUNS them. We send results back. Repeat.

Run from src2/:
    python day1_tools.py
"""

import json

from day1_first_call import call_model, user

MAX_STEPS = 5   # step cap: one bad question must never loop forever


# ---------------------------------------------------------------------------
# The tools. Fake data for now, but the SHAPE is what the real ones will have.
# ---------------------------------------------------------------------------

FAKE_DOCS = [
    {"id": "auto-match#1", "text": "Bank reconciliation auto-match was added in 2.3.0. It suggests "
                                   "matches between bank transactions and invoices."},
    {"id": "auto-match#2", "text": "Known issue on 2.3.1: auto-match does not convert foreign-currency "
                                   "amounts (BUG-2310-01). Use manual matching for now."},
    {"id": "rate-limits#1", "text": "API rate limits per minute: Starter 60, Professional 300, "
                                    "Enterprise 1,000."},
]

FAKE_BUGS = {
    "BUG-2310-01": {"title": "Bank reconciliation auto-match fails for multi-currency accounts",
                    "affected_version": "2.3.1", "fixed_in_version": None,
                    "severity": "Critical", "status": "Open"},
    "BUG-2100-02": {"title": "Recurring invoices skip a cycle across DST changes",
                    "affected_version": "2.1.0", "fixed_in_version": "2.3.1",
                    "severity": "High", "status": "Fixed"},
}


def search_docs(query):
    """Very dumb keyword search. Real search comes on Day 4."""
    words = set(query.lower().split())
    hits = [d for d in FAKE_DOCS if words & set(d["text"].lower().replace(",", "").split())]
    return {"results": hits[:2]} if hits else {"results": [], "note": "no matching documentation"}


def get_bug(bug_id):
    bug = FAKE_BUGS.get(bug_id.strip().upper())
    if bug is None:
        return {"error": f"no bug with id {bug_id}"}   # tell the model, don't crash
    return {"bug_id": bug_id, **bug}


# Our code decides which functions the model is allowed to trigger. Nothing else runs.
TOOL_FUNCTIONS = {"search_docs": search_docs, "get_bug": get_bug}

TOOLS = [{
    "functionDeclarations": [
        {
            "name": "search_docs",
            "description": "Search the InvoicePilot product documentation (help articles, release "
                           "notes). Use for questions about features, how things work, limits, "
                           "and known issues. Returns the most relevant passages with their ids.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "keywords to search for"}},
                "required": ["query"],
            },
        },
        {
            "name": "get_bug",
            "description": "Look up ONE bug in the bug tracker by its exact id, like BUG-2310-01. "
                           "Returns severity, status, affected version, and fixed-in version. "
                           "Use when you need the current status of a specific bug.",
            "parameters": {
                "type": "object",
                "properties": {"bug_id": {"type": "string", "description": "exact id, e.g. BUG-2310-01"}},
                "required": ["bug_id"],
            },
        },
    ]
}]

SYSTEM = (
    "You help sales engineers answer questions about InvoicePilot. "
    "Use the tools to find facts. Answer only from tool results, and mention the ids you used. "
    "If the tools don't give you the answer, say it is not in the documentation."
)


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------

def run_agent(question):
    print(f"\n{'=' * 70}\nQUESTION: {question}")
    contents = [user(question)]

    for step in range(1, MAX_STEPS + 1):
        data = call_model(contents, system=SYSTEM, tools=TOOLS, max_tokens=500)
        model_turn = data["candidates"][0]["content"]

        # Send the model's turn back EXACTLY as received (keeps thoughtSignature)
        contents.append(model_turn)

        calls = [p["functionCall"] for p in model_turn["parts"] if "functionCall" in p]

        if not calls:   # no tool requested = the model is done
            text = "".join(p.get("text", "") for p in model_turn["parts"])
            print(f"\n[step {step}] FINAL ANSWER:\n{text}")
            return text

        # The model asked for one or more tools. WE run them.
        responses = []
        for call in calls:
            name, args = call["name"], call.get("args", {})
            print(f"\n[step {step}] model asks: {name}({json.dumps(args)})")

            fn = TOOL_FUNCTIONS.get(name)
            if fn is None:
                result = {"error": f"unknown tool {name}"}       # never crash on a bad request
            else:
                try:
                    result = fn(**args)
                except TypeError as e:                           # wrong or missing arguments
                    result = {"error": f"bad arguments: {e}"}

            print(f"          we return: {json.dumps(result)[:200]}")
            responses.append({"functionResponse": {"name": name, "response": result}})

        contents.append({"role": "user", "parts": responses})

    print(f"\nSTOPPED: hit the step cap of {MAX_STEPS}")
    return None


if __name__ == "__main__":
    run_agent("Does auto-match work for multi-currency accounts on 2.3.1, and has the bug been fixed?")
    run_agent("Was the recurring invoice DST bug fixed? Its id is BUG-2100-02.")
    run_agent("What is the API rate limit on the Professional plan?")
    run_agent("What's the capital of France?")