# tests/test_checks.py
"""
Day 12, fast CI tier: the deterministic checks must catch what they claim to catch,
and must NOT fire on the two false alarms fixed on Day 11. No API key, no network.

Run:  python -m pytest -q
"""

from evals.checks import run_checks

INVITE = {"id": "getting-started/invite-users#0", "plans": None,
          "text": "Click Send Invite. The invite link expires after 7 days."}
RELEASE = {"id": "release-notes/v2.3.0#2", "plans": None,
           "text": "## Fixed in This Release BUG-2200-02 — API v2 rate limit headers missing"}
PRICE = {"id": "account-billing/plans-and-limits#1", "plans": None,
         "text": "| Enterprise | $40 |"}
SCHEDULE = {"id": "reports/report-schedules#0", "plans": ["Professional", "Enterprise"],
            "text": "Saved reports can be emailed daily, weekly, or monthly."}


def result(answer, status="answered", citations=None):
    import re
    cites = citations if citations is not None else re.findall(r"\[([^\]]+)\]", answer)
    return {"status": status, "answer": answer, "citations": cites, "not_covered": ""}


def failed(res, ev, question="q", cls="capability", ms=1000, cost=0.0005):
    return {k for k, (ok, _) in run_checks(res, ev, question, cls, ms, cost).items() if not ok}


def test_correct_answer_passes_everything():
    assert failed(result("The invite link expires after 7 days [getting-started/invite-users#0]."), [INVITE]) == set()


def test_wrong_number_is_caught():
    assert "cited_facts" in failed(result("It expires after 14 days [getting-started/invite-users#0]."), [INVITE])


def test_invented_citation_is_caught():
    assert "citations_resolve" in failed(result("It expires after 7 days [getting-started/invite#9]."), [INVITE])


def test_two_ids_in_one_bracket_is_caught():
    bad = result("It expires after 7 days [getting-started/invite-users#0, account-billing/plans-and-limits#1].")
    assert "citations_resolve" in failed(bad, [INVITE, PRICE])


def test_version_in_chunk_id_is_not_a_false_alarm():          # Day 11 fix (h-02)
    assert failed(result("BUG-2200-02 was fixed in 2.3.0 [release-notes/v2.3.0#2]."), [RELEASE]) == set()


def test_number_from_the_question_is_not_a_false_alarm():     # Day 11 fix (cf-06)
    res = result("Enterprise is $40 per seat; your sheet says $36 [account-billing/plans-and-limits#1].")
    assert failed(res, [PRICE], question="What does Enterprise cost? My sheet says $36.") == set()


def test_gated_answer_must_name_the_plan():
    res = result("Yes, saved reports can be emailed weekly [reports/report-schedules#0].")
    assert "edition_named" in failed(res, [SCHEDULE], cls="tier_gated")
    ok = result("Yes on Professional and Enterprise: reports can be emailed weekly [reports/report-schedules#0].")
    assert "edition_named" not in failed(ok, [SCHEDULE], cls="tier_gated")


def test_refusal_with_citations_breaks_schema():
    res = result("", status="not_in_documentation", citations=["getting-started/invite-users#0"])
    assert "schema" in failed(res, [INVITE])


def test_budgets():
    assert {"latency_budget", "cost_budget"} <= failed(
        result("It expires after 7 days [getting-started/invite-users#0]."), [INVITE], ms=9000, cost=0.01)
