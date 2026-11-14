# evals/checks.py
"""
Day 11: deterministic checks. Plain code, no model: free, instant, never disagrees with itself.
Run them before any judge. A case that fails here needs no judge to tell you it is broken.

    schema            valid fields, and status matches the answer (no empty "answered", no cited refusal)
    citations_resolve every cited id is one of the retrieved chunks, in the text and in the list
    cited_facts       numbers, codes and versions in a cited sentence appear in the chunk it cites
    edition_named     an answer about a plan-gated feature names the plan (Starter/Professional/Enterprise)
    latency_budget    retrieval + generation under BUDGET_MS
    cost_budget       one answer under BUDGET_USD
"""

import os
import re

STATUSES = {"answered", "partial", "not_in_documentation"}
PLANS = ("Starter", "Professional", "Enterprise")
ALL_PLANS = set(PLANS)
BUDGET_MS = float(os.getenv("BUDGET_MS", "5000"))
BUDGET_USD = float(os.getenv("BUDGET_USD", "0.002"))

CITE = re.compile(r"\[([^\]\s][^\]]*)\]")
# The facts most often wrong in a sentence: money, error and bug codes, versions, plain numbers.
KEY = re.compile(r"\$\d[\d,]*(?:\.\d+)?|\b(?:IP|BUG|TCKT|INC)-[\d-]+\b|\b\d+\.\d+\.\d+\b|\b\d[\d,]*(?:\.\d+)?\b")


def _plain(s):
    return s.replace(",", "").lower()


def cited_sentences(answer):
    """[(sentence without the [id] marks, [ids])] for sentences that carry at least one citation."""
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", answer):
        ids = CITE.findall(sent)
        if ids:
            out.append((CITE.sub("", sent), ids))
    return out


def run_checks(result, evidence, question, question_class, ms_total, cost):
    """evidence: [{id, text, plans}]. Returns {check name: (ok, detail)}."""
    by_id = {e["id"]: e for e in evidence}
    answer, status = result.get("answer", ""), result.get("status")
    checks = {}

    bad = [k for k in ("status", "citations", "answer", "not_covered") if k not in result]
    if status not in STATUSES:
        bad.append(f"status={status!r}")
    if status == "answered" and not answer.strip():
        bad.append("answered but empty")
    if status == "not_in_documentation" and result.get("citations"):
        bad.append("refusal with citations")
    checks["schema"] = (not bad, "; ".join(bad))

    ids = set(CITE.findall(answer)) | set(result.get("citations", []))
    ghost = sorted(i for i in ids if i not in by_id)
    checks["citations_resolve"] = (not ghost, ", ".join(ghost))

    missing = []
    asked = _plain(question)                 # a number the USER wrote ("my sheet says $36") needs no source
    for sent, sids in cited_sentences(answer):
        # the chunk id is part of its context: release-notes/v2.3.0#2 is about 2.3.0 even if the text never says it
        cited_text = _plain(" ".join(i + " " + by_id[i]["text"] for i in sids if i in by_id))
        for tok in (t.rstrip(",.") for t in KEY.findall(sent)):
            if _plain(tok) not in cited_text and _plain(tok) not in asked:
                missing.append(f"{tok} not in {'+'.join(sids)}")
    checks["cited_facts"] = (not missing, "; ".join(missing[:3]))

    cited = [by_id[i] for i in ids if i in by_id]
    gated = question_class == "tier_gated" or any(
        e.get("plans") and set(e["plans"]) != ALL_PLANS for e in cited)
    named = any(p.lower() in answer.lower() for p in PLANS)
    ok = not gated or status != "answered" or named
    checks["edition_named"] = (ok, "" if ok else "gated feature, no plan named")

    checks["latency_budget"] = (ms_total <= BUDGET_MS, f"{ms_total:.0f} ms")
    checks["cost_budget"] = (cost <= BUDGET_USD, f"${cost:.5f}")
    return checks
