# copilot/ingest/parsers/ticket_parser.py
"""Turn one helpdesk ticket export (JSON) into a clean document.

The JSON is already structured, so there is nothing to clean. The job is to
decide what becomes TEXT (what gets embedded and searched) and what becomes
METADATA (what we filter and rank on).
"""

import json
from pathlib import Path

SPEAKER = {"customer": "Customer", "agent": "Support agent"}


def parse_ticket(path: Path, root: Path) -> dict:
    t = json.loads(path.read_text(encoding="utf-8"))

    # Keep who said what. A customer's message is a question or a claim,
    # an agent's message is an answer. They are not equally trustworthy.
    lines = [f"# {t['subject']}"]
    for m in t["messages"]:
        lines.append(f"{SPEAKER.get(m['from'], m['from'])}: {m['body']}")
    if t.get("linked_bug_id"):
        lines.append(f"Linked bug: {t['linked_bug_id']}")

    rel = path.relative_to(root)
    return {
        "doc_id": f"support_tickets/{t['ticket_id']}",
        "title": t["subject"],
        "source_type": "support_ticket",
        "source_path": str(rel),
        "section": "support_tickets",
        "last_updated": t["messages"][-1]["sent_at"][:10],
        "applies_to": t.get("product_version"),   # the version the customer was on
        "plans": None,                            # NOT the customer's plan; see customer_plan
        "author": None,
        "version": None,
        "customer_plan": t.get("plan"),
        "linked_bug_id": t.get("linked_bug_id"),
        "text": "\n".join(lines),
    }