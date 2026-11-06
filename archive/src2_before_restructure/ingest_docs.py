# src2/ingest_docs.py
"""
Day 3, Lesson 4: parse every document, write documents.jsonl, report metadata coverage.
Day 7: corpus v2 adds support tickets (JSON), engineering notes (Markdown), sales docs (DOCX).

Run from src2/:
    python ingest_docs.py

Safe to re-run: it only reads local files.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from parse_docx import parse_docx
from parse_html import parse_html_page
from parse_markdown import parse_markdown
from parse_pdf import parse_release_notes
from parse_ticket import parse_ticket

DATA = Path("../data/invoicepilot")
CORPUS = DATA / "corpus"
HELP_CENTER = CORPUS / "help_center"
RELEASE_NOTES = CORPUS / "release_notes"      # NOT data_package/docs: same PDFs
TICKETS = CORPUS / "support_tickets"
ENGINEERING = CORPUS / "engineering"
SALES = CORPUS / "sales"
OUT = DATA / "processed" / "documents.jsonl"

FIELDS = ["source_type", "last_updated", "applies_to", "plans", "version", "author", "status"]

# Page types where a missing applies_to is a real gap. Tickets carry the customer's
# version; internal notes and sales docs have no version by design.
VERSIONED_TYPES = {"help_article", "api_reference", "troubleshooting", "faq", "guide"}


def collect():
    docs = [parse_html_page(p, HELP_CENTER) for p in sorted(HELP_CENTER.rglob("*.html"))]
    docs += [parse_release_notes(p, DATA) for p in sorted(RELEASE_NOTES.glob("*.pdf"))]
    docs += [parse_ticket(p, CORPUS) for p in sorted(TICKETS.glob("*.json"))]
    docs += [parse_markdown(p, CORPUS) for p in sorted(ENGINEERING.glob("*.md"))]
    docs += [parse_docx(p, CORPUS) for p in sorted(SALES.glob("*.docx"))]

    if not docs:
        sys.exit(f"no documents found under {CORPUS}")
    if leaked := [d["source_path"] for d in docs if "answer_key" in d["source_path"]]:
        sys.exit(f"answer key leaked into the corpus: {leaked}")
    if dupes := [i for i, n in Counter(d["doc_id"] for d in docs).items() if n > 1]:
        sys.exit(f"duplicate doc_ids: {dupes}")
    if empty := [d["doc_id"] for d in docs if len(d["text"].split()) < 20]:
        print(f"WARNING: suspiciously short documents: {empty}")
    return docs


def report(docs):
    words = sum(len(d["text"].split()) for d in docs)
    print(f"\n{len(docs)} documents, {words:,} words\n")

    by_type = defaultdict(list)
    for d in docs:
        by_type[d["source_type"]].append(d)

    print(f"{'source_type':17s} {'docs':>5s}  " + "  ".join(f"{f:>12s}" for f in FIELDS))
    for st, group in sorted(by_type.items()):
        cells = []
        for f in FIELDS:
            have = sum(1 for d in group if d.get(f))
            cells.append(f"{have:>3d}/{len(group):<3d}{have / len(group):>5.0%}")
        print(f"{st:17s} {len(group):>5d}  " + "  ".join(f"{c:>12s}" for c in cells))

    print("\nmissing applies_to (help center pages only):")
    for d in docs:
        if d["source_type"] in VERSIONED_TYPES and not d["applies_to"]:
            print(f"  - {d['doc_id']}")


def main():
    docs = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    report(docs)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()