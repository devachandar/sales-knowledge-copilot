# copilot/ingest/parsers/markdown_parser.py
"""Turn one internal engineering note (Markdown with a YAML front matter
block) into a clean document.

We read the front matter by hand instead of with a YAML library: titles like
"Postmortem INC-2026-019: Auto-match fails" contain ": ", which is a YAML
syntax error when the value is not quoted. Hand-written front matter is often
not valid YAML, so a strict parser would crash on real files.
"""

from pathlib import Path


def _front_matter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    meta = {}
    for line in raw[3:end].strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)          # split on the FIRST colon only
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            value = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        meta[key.strip()] = value
    return meta, raw[end + 4:].strip()


def parse_markdown(path: Path, root: Path) -> dict:
    meta, body = _front_matter(path.read_text(encoding="utf-8"))
    rel = path.relative_to(root)
    title = meta.get("title") or path.stem
    if not body.startswith("# "):
        body = f"# {title}\n{body}"
    return {
        "doc_id": str(rel.with_suffix("")),
        "title": title,
        "source_type": "internal",
        "source_path": str(rel),
        "section": rel.parts[0],
        "last_updated": meta.get("last_updated"),
        "applies_to": None,
        "plans": None,
        "author": meta.get("owner"),
        "version": None,
        "doc_type": meta.get("doc_type"),
        "audience": meta.get("audience"),
        "status": meta.get("status"),
        "related_bugs": meta.get("related_bugs"),
        "text": body,
    }