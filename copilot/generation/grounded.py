# copilot/generation/grounded.py
"""
Day 2, Lesson 1: a versioned grounded prompt, real evidence from the corpus.

Run from the project root:
    python -m copilot.generation.grounded
"""

import json
import re

import os

from copilot.config import HELP_CENTER_DIR, PROMPTS_DIR
from copilot.llm.client import call_model, user


PROMPT_VERSION = os.getenv("PROMPT_VERSION", "grounded_v4")   # Day 12: v3 fixed the Day 11 patterns, v4 its side effects

SYSTEM = (PROMPTS_DIR / f"{PROMPT_VERSION}.md").read_text(encoding="utf-8")

HELP_CENTER = HELP_CENTER_DIR

SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["answered", "partial", "not_in_documentation"]},
        "citations": {"type": "array", "items": {"type": "string"},
                      "description": "ids of the evidence blocks used"},
        "answer": {"type": "string", "description": "the answer with [id] citations; empty if not answered"},
        "not_covered": {"type": "string",
                        "description": "which part of the question the evidence does not cover; empty if none"},
    },
    "required": ["status", "citations", "answer", "not_covered"],
}


def load_page(doc_id):
    """Quick and rough: pull the article text out of one help page. Day 3 does this properly."""
    html = (HELP_CENTER / f"{doc_id}.html").read_text(encoding="utf-8")
    article = re.search(r"<article>(.*?)</article>", html, re.S).group(1)
    text = re.sub(r"<[^>]+>", " ", article)
    return {"id": doc_id, "text": re.sub(r"\s+", " ", text).strip()}


def build_user_message(question, evidence):
    blocks = "\n\n".join(f'<evidence id="{e["id"]}">\n{e["text"]}\n</evidence>' for e in evidence)
    return f"{blocks}\n\nQuestion: {question}"


def ask(question, evidence):
    data = call_model(
        [user(build_user_message(question, evidence))],
        system=SYSTEM,
        max_tokens=800,
        extra_config={"responseMimeType": "application/json", "responseJsonSchema": SCHEMA},
    )
    cand = data["candidates"][0]
    if cand.get("finishReason") != "STOP":
        raise RuntimeError(f"finishReason={cand.get('finishReason')}")
    result = json.loads("".join(p.get("text", "") for p in cand["content"]["parts"]))
    usage = data.get("usageMetadata", {})
    return result, usage


def check(result, evidence):
    """Meaning checks the schema can't do."""
    valid = {e["id"] for e in evidence}
    problems = [f"invented citation: {c}" for c in result["citations"] if c not in valid]
    cited_in_text = set(re.findall(r"\[([^\]]+)\]", result["answer"]))
    problems += [f"cited in text but not in list: {c}" for c in cited_in_text - set(result["citations"])]
    if result["status"] != "not_in_documentation" and not result["citations"]:
        problems.append("answered without citations")
    return problems


TESTS = [
    ("How many invoices can I select in one bulk action?",
     ["invoicing/bulk-invoice-actions"]),
    ("What is the API rate limit on the Starter plan, and what error do I get when I go over?",
     ["api/api-rate-limits", "api/api-errors"]),
    ("Can a Starter customer brand their client portal with their logo?",
     ["client-portal/portal-branding", "client-portal/client-portal-overview"]),
]


if __name__ == "__main__":
    print(f"prompt version: {PROMPT_VERSION}")
    for question, doc_ids in TESTS:
        evidence = [load_page(d) for d in doc_ids]
        result, usage = ask(question, evidence)
        print(f"\n{'=' * 70}\nQ: {question}")
        print(json.dumps(result, indent=2))
        print(f"tokens in={usage.get('promptTokenCount')} out={usage.get('candidatesTokenCount')}")
        problems = check(result, evidence)
        print("checks:", "OK" if not problems else problems)