# Golden set

The fixed instrument every change is measured against. 146 cases in `evals/questions/`,
checked by `python -m evals.check_questions` (built 2026-11-06, Day 9).

## Composition

| Slice | Dev | Test | Total | Hard | Expected behavior |
|---|---|---|---|---|---|
| capability | 16 | 4 | 20 | 7 | answer |
| exact_token | 20 | 6 | 26 | 20 | answer |
| tier_gated | 15 | 3 | 18 | 6 | answer, naming the plan |
| temporal | 16 | 2 | 18 | 10 | answer, naming the version |
| multi_hop | 6 | 6 | 12 | 10 | answer (one fact unlocks the next) |
| synthesis | 5 | 5 | 10 | 6 | answer (combine several sources) |
| out_of_scope | 5 | 7 | 12 | 3 | refuse, saying why |
| conflict | 5 | 5 | 10 | 6 | answer and flag the disagreement |
| injection | 4 | 6 | 10 | 9 | resist the embedded instruction |
| non_official | 8 | 2 | 10 | 7 | answer from internal or sales docs |
| **Total** | **100** | **46** | **146** | **84** | |

By behavior: answer 114, refuse 12, flag_conflict 10, resist 10.

## Rules

- **Test split is sealed.** Every eval runs on `dev` by default. Run `SPLIT=test` only at milestones
  (Days 15, 22, 30), never while tuning. All 46 test cases are new; the 68 cases from Days 2–7 are dev,
  because every Day 6–8 decision was tuned on them.
- **Evidence quotes, not chunk ids.** Each answerable case stores 1+ exact quotes from its expected docs,
  so the "expected chunk" survives re-chunking. The checker confirms every quote exists word for word.
- **must_include is the core fact only** (failures.md K1, K3), and it must appear in the expected answer.
- **refuse** cases have no expected docs; **flag_conflict** cases need evidence from 2+ docs;
  **resist** cases carry the attack text in `injected`.
- **targets** tags each case with the failure category it tests (taxonomy below), so a score drop says
  which kind of failure came back.

## Failure taxonomy (from failures.md and Days 4–8)

| Layer | Categories |
|---|---|
| Retrieval | lookalike_token, low_authority_source, version_competition, vocabulary_mismatch, chunk_context, plan/version_filter_removes_evidence |
| Generation | wrong_attribution, hidden_conflict, incomplete_answer, format breakage |
| Behavior | scope_boundary, customer_specific, commitment, indirect_injection, prompt_leak, tool_abuse, false_premise |
| Measurement | answer-key gaps, single-run noise |

## Verification status

All 146 cases have `verified: true` with `verified_by: "claude-review-2026-11-06"`: every expected answer
was checked against the corpus, and claims that only internal or community pages support were removed
from answers to official-page cases. **A human spot-check is still pending.** Day 10's hand-labeling of
25 outputs is the natural place to do it; change `verified_by` to your name on cases you confirm.

## Known gaps

- Only 7 non-official and 10 conflict cases; enough to show a blind spot, not to tune on.
- Customer-data multi-hop (SQL tables) is not covered yet; the tables lack the corpus v2 bugs (Day 14).
- Retrieval evals skip cases with no expected docs (refusals, one injection case); those are scored on answers (Days 10, 17, 24).
