# src2/chunkers.py
"""Chunking strategies. Each takes text and returns a list of chunk strings."""
import re

SIZE = 500
OVERLAP = 100


TABLE_MAX = 1200     # a table stays whole up to this size
MIN_CHUNK = 150      # a chunk shorter than this keeps filling into the next section
HEADING = re.compile(r"^#{1,6} ")

HEADING_PARTS = re.compile(r"^(#{1,6}) (.*)")

# ---------------------------------------------------------------- fixed-size
def fixed(text, size=SIZE, overlap=OVERLAP):
    """Cut every `size` characters, moving each cut back to the nearest space."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            space = text.rfind(" ", start, end)
            if space > start:
                end = space
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
        while start < end and not text[start - 1].isspace():
            start += 1
    return chunks


# ----------------------------------------------------------------- recursive
SEPARATORS = ["\n\n", "\n", ". ", " "]   # biggest break first


def _split(text, size, seps):
    """Cut at the biggest separator; re-cut any piece that is still too long."""
    if len(text) <= size:
        return [text]
    if not seps:                                   # nothing left: hard cut
        return [text[i:i + size] for i in range(0, len(text), size)]
    sep, rest = seps[0], seps[1:]
    parts = text.split(sep)
    if len(parts) == 1:                            # separator not present
        return _split(text, size, rest)
    pieces = []
    for i, p in enumerate(parts):
        piece = p + (sep if i < len(parts) - 1 else "")   # keep the separator
        pieces += _split(piece, size, rest) if len(piece) > size else [piece]
    return pieces


def _merge(pieces, size, overlap):
    """Glue neighbouring pieces up to `size`; start each chunk with a little of the last one."""
    chunks, cur = [], []
    for p in pieces:
        if cur and len("".join(cur)) + len(p) > size:
            chunks.append("".join(cur).strip())
            tail = []
            for q in reversed(cur):                # overlap = last whole pieces up to `overlap` chars
                if len("".join(tail)) + len(q) > overlap:
                    break
                tail.insert(0, q)
            cur = tail
        cur.append(p)
    if cur:
        chunks.append("".join(cur).strip())
    return [c for c in chunks if c]


def recursive(text, size=SIZE, overlap=OVERLAP):
    return _merge(_split(text, size, SEPARATORS), size, overlap)

# ----------------------------------------------------------- structure-aware
# import re

# TABLE_MAX = 1200     # a table stays whole up to this size
# MIN_CHUNK = 150      # a chunk shorter than this keeps filling into the next section
# HEADING = re.compile(r"^#{1,6} ")


def _sections(text):
    """Split the document into sections, each starting at a heading line."""
    secs, cur = [], []
    for line in text.split("\n"):
        if HEADING.match(line) and cur:
            secs.append(cur)
            cur = []
        cur.append(line)
    if cur:
        secs.append(cur)
    return secs


def _units(lines):
    """Group lines into units that must not be split: a whole table, a whole code block, or one line."""
    units, i = [], 0
    while i < len(lines):
        if lines[i].startswith("|"):                       # table: all consecutive | lines
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
        elif lines[i].startswith("```"):                   # code block: up to the closing fence
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            j += 1
        else:                                              # one ordinary line
            j = i + 1
        units.append(lines[i:j])
        i = j
    return units


def _split_table(rows, limit):
    """Split a huge table by rows, repeating the header (first 2 lines) in every piece."""
    header, body, pieces, cur = rows[:2], rows[2:], [], []
    for r in body:
        if cur and len("\n".join(header + cur + [r])) > limit:
            pieces.append(header + cur)
            cur = []
        cur.append(r)
    if cur:
        pieces.append(header + cur)
    return pieces


def structure_aware(text, size=SIZE, table_max=TABLE_MAX, min_chunk=MIN_CHUNK):
    # 1. Turn the document into pieces; each remembers the heading it sits under.
    pieces, heading = [], ""
    for sec in _sections(text):
        if HEADING.match(sec[0]):
            heading, body, starts = sec[0], sec[1:], True
        else:
            body, starts = sec, False
        first = True
        for u in _units(body) or [[]]:
            is_table = bool(u) and u[0].startswith("|")
            parts = _split_table(u, table_max) if is_table and len("\n".join(u)) > table_max else [u]
            for part in parts:
                block = "\n".join(part)
                if first and starts:                       # the heading travels with its first block
                    block = (heading + "\n" + block).strip()
                pieces.append((block, heading, first and starts))
                first = False

    # 2. Pack pieces into chunks: cut at a new section when the chunk is big enough,
    #    never go over `size` (except one whole table), and repeat the heading when a
    #    section continues into a new chunk.
    chunks, cur = [], ""
    for block, head, new_section in pieces:
        if not block:
            continue
        too_big = cur and len(cur) + 1 + len(block) > size
        section_break = cur and new_section and len(cur) >= min_chunk
        if too_big or section_break:
            chunks.append(cur)
            cur = "" if new_section or not head else head
        cur = (cur + "\n" + block).strip()
    if cur:
        chunks.append(cur)
    return chunks


def heading_paths(text):
    """Map each heading line to its path, e.g. ['Line items...', 'Long invoices in PDF', 'Workaround']."""
    paths, stack = {}, []
    for line in text.split("\n"):
        m = HEADING_PARTS.match(line)
        if m:
            level = len(m.group(1))
            stack = [s for s in stack if s[0] < level] + [(level, m.group(2).strip())]
            paths.setdefault(line, [name for _, name in stack])
    return paths


def add_context(chunks, title, text):
    """Put 'Title > Section > Subsection' on the first line of every chunk."""
    paths = heading_paths(text)
    out = []
    for c in chunks:
        first_line = c.split("\n", 1)[0]
        names = [title] + paths.get(first_line, [])
        header = " > ".join(dict.fromkeys(n for n in names if n))   # drop repeats, keep order
        if header == title and first_line == f"# {title}":
            out.append(c)                                          # title already on line 1
        else:
            out.append(f"{header}\n{c}")
    return out

STRATEGIES = {
    "fixed-500":       lambda text, title: fixed(text),
    "recursive-500":   lambda text, title: recursive(text),
    "structure-aware": lambda text, title: structure_aware(text),
    "structure-ctx":   lambda text, title: add_context(structure_aware(text), title, text),
}