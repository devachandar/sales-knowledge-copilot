# copilot/retrieval/authority.py
"""
Day 7, Lesson 4: source authority and diversity, applied AFTER relevance scoring.

Relevance (reranker or RRF) answers "does this chunk answer the question?"
Authority answers "should we trust where it came from?"
Diversity answers "are the top 5 just copies of the same thing?"
"""

import json
from collections import Counter
from copilot.config import DOCUMENTS_FILE

DOCS = DOCUMENTS_FILE

OFFICIAL = {"help_article", "api_reference", "troubleshooting", "faq", "guide", "release_notes"}
INTERNAL = {"internal", "sales_enablement"}
# Everything else (support_ticket, community) is low authority.

# Bonus in STANDARD DEVIATIONS of the relevance scores, so it means the same
# thing whether relevance came from the reranker (logits) or from RRF (0.01-0.03).
PRIOR = {"official": 1.0, "internal": 0.0, "low": -1.0}
TIER_ORDER = {"official": 0, "internal": 1, "low": 2}

CAPS = {"support_ticket": 1, "community": 1}   # at most this many in the top 5

# chunk.py did not copy `status` onto chunks, so look it up per document.
_STATUS = {}
if DOCS.exists():
    for line in DOCS.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        _STATUS[d["doc_id"]] = d.get("status")


def tier(chunk):
    """official / internal / low. Stale sources are low, whatever their type."""
    if chunk["doc_id"].startswith("legacy/") or _STATUS.get(chunk["doc_id"]) in ("archived", "draft"):
        return "low"
    if chunk["source_type"] in OFFICIAL:
        return "official"
    if chunk["source_type"] in INTERNAL:
        return "internal"
    return "low"


def zscores(values):
    """Turn any scores into 'how many standard deviations above the average'."""
    n = len(values)
    mean = sum(values) / n
    std = (sum((v - mean) ** 2 for v in values) / n) ** 0.5 or 1.0
    return [(v - mean) / std for v in values]


def with_authority(ids, scores, chunk, prior=PRIOR):
    """Soft: relevance (z-scored) + a bonus or penalty by tier. Returns ids, best first."""
    z = zscores(scores)
    adjusted = [zi + prior[tier(chunk[c])] for zi, c in zip(z, ids)]
    return [c for _, c in sorted(zip(adjusted, ids), key=lambda x: -x[0])]


def hard_tiers(ids, scores, chunk):
    """Hard: every official chunk above every internal chunk above every low one."""
    order = sorted(zip(ids, scores), key=lambda x: (TIER_ORDER[tier(chunk[x[0]])], -x[1]))
    return [c for c, _ in order]


def diversify(ids, chunk, k=5, caps=CAPS):
    """Top k with at most one chunk per document and per-type caps. The rest keep their order."""
    top, seen_docs, used = [], set(), Counter()
    for c in ids:
        ch = chunk[c]
        if ch["doc_id"] in seen_docs or used[ch["source_type"]] >= caps.get(ch["source_type"], k):
            continue
        top.append(c)
        seen_docs.add(ch["doc_id"])
        used[ch["source_type"]] += 1
        if len(top) == k:
            break
    for c in ids:                       # not enough diverse chunks: fill up in order
        if len(top) == k:
            break
        if c not in top:
            top.append(c)
    return top + [c for c in ids if c not in top]