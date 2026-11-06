# copilot/ingest/parsers/docx_parser.py
"""Turn one Word document (sales enablement) into a clean document.

Two things make .docx different from HTML:
  1. Metadata lives in the file's "core properties" (title, author, keywords,
     comments), not in the text.
  2. doc.paragraphs and doc.tables are two separate lists, so reading them one
     after the other loses where each table sat. We walk the body in order.
"""

import re
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

BOILERPLATE = ("Owner:", "Internal: for InvoicePilot sales")


def _kv(s: str) -> dict:
    """'status=archived' -> {'status': 'archived'}"""
    return dict(re.findall(r"(\w+)=([\w\-]+)", s or ""))


def _table_to_md(t: Table) -> list[str]:
    rows = ["| " + " | ".join(c.text.strip() for c in r.cells) + " |" for r in t.rows]
    if rows:
        n = len(t.rows[0].cells)
        rows.insert(1, "|" + " --- |" * n)
    return rows


def _para_to_md(p: Paragraph, counter: list[int]) -> str | None:
    text = p.text.strip()
    if not text or text.startswith(BOILERPLATE):
        return None
    style = p.style.name
    if style.startswith("Heading"):
        level = int(style.split()[-1]) if style.split()[-1].isdigit() else 2
        return "#" * level + " " + text
    if style == "List Bullet":
        return f"- {text}"
    if style == "List Number":
        counter[0] += 1
        return f"{counter[0]}. {text}"
    return text


def parse_docx(path: Path, root: Path) -> dict:
    d = Document(path)
    props = d.core_properties
    lines, counter = [], [0]
    for el in d.element.body.iterchildren():          # body in document order
        tag = el.tag.split("}")[-1]
        if tag == "p":
            p = Paragraph(el, d)
            if p.style.name != "List Number":
                counter[0] = 0                         # a new numbered list starts at 1
            line = _para_to_md(p, counter)
            if line:
                lines.append(line)
        elif tag == "tbl":
            lines.extend(_table_to_md(Table(el, d)))

    rel = path.relative_to(root)
    return {
        "doc_id": str(rel.with_suffix("")),
        "title": props.title or path.stem,
        "source_type": props.subject or "sales_enablement",
        "source_path": str(rel),
        "section": rel.parts[0],
        "last_updated": _kv(props.comments).get("last_updated"),
        "applies_to": None,
        "plans": None,
        "author": props.author or None,
        "version": None,
        "audience": "internal",
        "status": _kv(props.keywords).get("status"),
        "text": "\n".join(lines),
    }