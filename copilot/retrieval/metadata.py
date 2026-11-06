# copilot/retrieval/metadata.py
"""
Day 6: metadata filtering and boosting on vector candidates (version, plan, community posts).

Used by V3 in copilot/retrieval/pipeline.py. The experiment that compares the modes
is evals/retrieval/metadata_eval.py.
"""

K, FETCH, BOOST = 5, 50, 0.02
MODES = ["none", "no-community", "hard", "hard+no-community", "soft", "soft+no-community"]


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def covers_version(applies, version):
    """'2.3.0+' = that version and later; '2.1.0' = exactly; empty = everything."""
    if version == "none" or not applies:
        return True
    try:
        if applies.endswith("+"):
            return vtuple(version) >= vtuple(applies[:-1])
        return vtuple(version) == vtuple(applies)
    except ValueError:
        return True                       # a label we can't read: never filter on it


def covers_plan(plans, plan):
    return plan == "none" or not plans or plan in plans


def apply_mode(candidates, filt, mode):
    out = []
    for c in candidates:
        m = c["metadata"]
        community = m.get("source_type") == "community"
        match = covers_version(m.get("applies_to"), filt["version"]) and covers_plan(m.get("plans"), filt["plan"])
        if "no-community" in mode and community:
            continue
        if mode.startswith("hard") and not match:
            continue
        score = c["score"]
        if mode.startswith("soft"):
            score += BOOST if (match and filt != {"version": "none", "plan": "none"}) else 0
            score -= BOOST if community else 0
        out.append({**c, "score": score})
    return sorted(out, key=lambda x: x["score"], reverse=True)[:K]
