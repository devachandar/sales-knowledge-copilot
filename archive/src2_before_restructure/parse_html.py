# src2/parse_html.py
"""
Day 3, Lesson 2: turn one crawled help-center page into clean text + metadata.

Two jobs:
  1. Throw away boilerplate (menu, search box, breadcrumb, widget, footer, cookies).
  2. Pull out metadata: meta tags first, then what the page shows.

Text keeps its structure as light markdown so Day 5 can chunk on headings.
"""

import re
from pathlib import Path

from lxml import html as lxml_html

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _text(el):
    return " ".join(el.text_content().split())


def _block_to_md(el):
    tag = el.tag
    if tag in ("h1", "h2", "h3"):
        return ["#" * int(tag[1]) + " " + _text(el)]
    if tag == "p":
        return [_text(el)]
    if tag == "ul":
        return [f"- {_text(li)}" for li in el.findall("li")]
    if tag == "ol":
        return [f"{i}. {_text(li)}" for i, li in enumerate(el.findall("li"), 1)]
    if tag == "table":
        rows = []
        for tr in el.iter("tr"):
            cells = [_text(c) for c in tr if c.tag in ("th", "td")]
            rows.append("| " + " | ".join(cells) + " |")
        if rows:
            n = rows[0].count("|") - 1
            rows.insert(1, "|" + " --- |" * n)
        return rows
    if tag == "pre":
        return ["```", el.text_content().rstrip(), "```"]
    if tag == "div" and "callout" in (el.get("class") or ""):
        return [f"> {_text(el)}"]
    return [_text(el)] if _text(el) else []


def parse_html_page(path: Path, root: Path) -> dict:
    tree = lxml_html.fromstring(path.read_bytes())
    meta = {m.get("name"): m.get("content") for m in tree.iter("meta") if m.get("name")}

    article = tree.find(".//article")
    if article is None:
        raise ValueError(f"no <article> in {path}")   # fail loudly, never guess
    title = _text(article.find("h1"))

    # The visible header lines are metadata fallbacks. Read them, then REMOVE them
    # from the text, because metadata is not content.
    shown = {}
    for cls in ("updated", "applies", "plans", "byline"):
        el = article.find(f".//p[@class='{cls}']")
        if el is not None:
            shown[cls] = _text(el)
            el.getparent().remove(el)

    lines = []
    for el in article:
        lines.extend(_block_to_md(el))
    text = "\n".join(l for l in lines if l.strip())
    # print(repr(text))

    rel = path.relative_to(root)

    # --- metadata, each with a fallback --------------------------------------
    source_type = meta.get("source-type")
    author = None
    if "byline" in shown:                       # community pages have no meta tags
        source_type = source_type or "community"
        m = re.match(r"Posted by (\S+)", shown["byline"])
        author = m.group(1) if m else None

    last_updated = meta.get("last-updated")
    if not last_updated:
        m = DATE_RE.search(shown.get("updated", "") or shown.get("byline", ""))
        last_updated = m.group(0) if m else None

    applies = meta.get("applies-to-version")
    if not applies and "applies" in shown:
        applies = shown["applies"].replace("Applies to: InvoicePilot", "").strip()

    plans_raw = meta.get("available-on-plans") or shown.get("plans", "").replace("Available on:", "")
    plans = [p.strip() for p in plans_raw.split(",") if p.strip()] or None

    return {
        "doc_id": meta.get("doc-id") or str(rel.with_suffix("")),
        "title": title,
        "source_type": source_type,
        "source_path": str(rel),
        "section": rel.parts[0],
        "last_updated": last_updated,
        "applies_to": applies,
        "plans": plans,
        "author": author,
        "version": None,          # only release notes have one; set by the PDF parser
        "text": text,
    }


if __name__ == "__main__":
    import json
    root = Path("../data/invoicepilot/corpus/help_center")
    for doc_id in ["bank-reconciliation/auto-match",      # normal page with a callout
                "account-billing/plans-and-limits",    # tables, no applies-to
                "community/bulk-send-tips"]:           # no meta tags at all
        d = parse_html_page(root / f"{doc_id}.html", root)
        print("=" * 70)
        print(json.dumps({k: v for k, v in d.items() if k != "text"}, indent=2))
        print("--- text ---")
        print(d["text"])