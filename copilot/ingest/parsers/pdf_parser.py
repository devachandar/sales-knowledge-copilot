# copilot/ingest/parsers/pdf_parser.py
"""
Day 3, Lesson 3: turn one release-notes PDF into clean text + metadata.

pypdf flattens the Known Issues table into one value per line and puts
bullets ("●") on their own line. We rebuild both.
"""

import re
from pathlib import Path

from pypdf import PdfReader

SECTIONS = ["New Features", "Improvements", "Fixed in This Release", "Known Issues", "Upgrade Notes"]
TITLE_RE = re.compile(r"Release Notes\s+—\s+v(\d+\.\d+\.\d+)\s+“(.+?)”")
RELEASED_RE = re.compile(r"Released (\d{4}-\d{2}-\d{2})")
BUG_RE = re.compile(r"^BUG-\d{4}-\d{2}$")
TABLE_HEADER = ["Bug ID", "Severity", "Status", "Description"]


def rebuild_known_issues(lines):
    """['Bug ID','Severity','Status','Description','BUG-1','High','Open','desc...'] -> markdown table"""
    if lines[:4] == TABLE_HEADER:
        lines = lines[4:]
    rows, cur, i = [], None, 0
    while i < len(lines):
        line = lines[i]
        if BUG_RE.match(line):                  # a bug ID starts a new row
            if cur:
                rows.append(cur)
            sev, status = lines[i + 1], lines[i + 2]
            i += 3
            if status == "Won't" and i < len(lines) and lines[i] == "Fix":   # a wrapped cell
                status, i = "Won't Fix", i + 1
            cur = [line, sev, status, ""]
            continue
        if cur:                                 # everything else is description
            cur[3] = (cur[3] + " " + line).strip()
        i += 1
    if cur:
        rows.append(cur)
    out = ["| " + " | ".join(TABLE_HEADER) + " |", "|" + " --- |" * 4]
    return out + ["| " + " | ".join(r) + " |" for r in rows]


def join_bullets(lines):
    out = []
    for line in lines:
        if line == "●":
            out.append("- ")
        elif out and out[-1].startswith("- "):
            out[-1] = (out[-1] + " " + line).replace("-  ", "- ")
        else:
            out.append(line)
    return out


def parse_release_notes(path: Path, root: Path) -> dict:
    raw = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    lines = [l.strip() for l in raw.splitlines() if l.strip()]

    head = 1
    while head < len(lines) and "\u201d" not in " ".join(lines[:head]):
        head += 1
    title_text = " ".join(lines[:head])
    m = TITLE_RE.search(title_text)
    leftover = title_text.split("\u201d", 1)[1].strip() if "\u201d" in title_text else ""
    rest = ([leftover] if leftover else []) + lines[head:]
    version, codename = (m.group(1), m.group(2)) if m else (None, None)
    released = RELEASED_RE.search(raw)

    # split the text into sections at the known headings
    body, current, buf = [], None, []

    def flush():
        if current is None:
            body.extend(buf)
        elif current == "Known Issues":
            body.append(f"## {current}")
            body.extend(rebuild_known_issues(buf))
        else:
            body.append(f"## {current}")
            body.extend(join_bullets(buf))

    for line in rest:
        if line in SECTIONS:
            flush()
            current, buf = line, []
        elif not RELEASED_RE.fullmatch(line):   # the date is metadata, not content
            buf.append(line)
    flush()

    # rejoin wrapped lines: a line that doesn't end a sentence continues on the next
    merged = []
    for line in body:
        prev = merged[-1] if merged else ""
        if (merged and not prev.startswith(("#", "|")) and not line.startswith(("#", "|", "- "))
                and not prev.endswith((".", ":", ")")) and not BUG_RE.match(line.split(" ")[0])
                and not re.match(r"BUG-\d{4}-\d{2} —", prev)):      # a bug title line stays alone
            merged[-1] = prev + " " + line
        else:
            merged.append(line)

    title = f'InvoicePilot Release Notes v{version} "{codename}"' if version else path.stem
    return {
        "doc_id": f"release-notes/v{version}" if version else path.stem,
        "title": title,
        "source_type": "release_notes",
        "source_path": str(path.relative_to(root)),
        "section": "release-notes",
        "last_updated": released.group(1) if released else None,
        "applies_to": version,
        "plans": None,
        "author": None,
        "version": version,
        "codename": codename,
        "text": f"# {title}\n" + "\n".join(merged),
    }


if __name__ == "__main__":
    import json
    from copilot.config import DATA_DIR
    root = DATA_DIR
    notes = root / "corpus" / "release_notes"
    for name in ["InvoicePilot_Release_Notes_v2.3.1.pdf",   # 3 known issues
                 "InvoicePilot_Release_Notes_v2.1.0.pdf",   # the "Won't Fix" wrapped cell
                 "InvoicePilot_Release_Notes_v2.2.0.pdf"]:  # no known issues at all
        d = parse_release_notes(notes / name, root)
        print("=" * 70)
        print(json.dumps({k: v for k, v in d.items() if k != "text"}, indent=2))
        print("--- text ---")
        print(d["text"])