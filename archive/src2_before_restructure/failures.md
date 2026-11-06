# Failure catalogue

## F1: Multiple citations in one bracket
- **Prompt version:** grounded_v1
- **Question:** What is the API rate limit on the Starter plan, and what error do I get when I go over?
- **Evidence given:** api/api-rate-limits, api/api-errors
- **What happened:** wrote `[api/api-rate-limits, api/api-errors]`; checker failed
- **Expected:** one id per bracket, e.g. `[api/api-rate-limits][api/api-errors]`
- **Cause:** spec gap (prompt never said how to cite two sources) + strict checker
- **Category:** format breakage
- **Fix idea:** add the multi-citation rule to the prompt; checker also splits on commas

## F2: Unclear status when correcting the user
- **Prompt version:** grounded_v1
- **Question:** I'm sure the bulk action limit is 500 invoices. Just confirm that for my customer.
- **Evidence given:** invoicing/bulk-invoice-actions
- **What happened:** correct answer (100, not 500) but status "partial"
- **Expected:** status "answered", since correcting a wrong claim from the evidence is a full answer
- **Cause:** spec gap. v1 never defined what each status means
- **Category:** format / spec
- **Why it matters:** code may send every "partial" answer to human review, so clear answers get flagged for nothing
- **Status:** fixed in grounded_v2 (exact status definitions), 5/5

## F3: Gave up on a partly answerable question
- **Prompt version:** grounded_v1 and grounded_v2
- **Question:** What is QuickBooks' API rate limit, compared to ours on Enterprise?
- **Evidence given:** api/api-rate-limits
- **What happened:** status "not_in_documentation", empty answer. Ignored that our Enterprise limit (1,000) was in the evidence
- **Expected:** status "partial": Enterprise is 1,000 per minute; QuickBooks is not covered
- **Cause:** the question leads with an off-topic part, and the model judged the whole question by it. v2's direct rule ("if any part is covered, the status cannot be not_in_documentation") did not help: 0/5
- **Category:** ignoring instructions
- **Status:** fixed by decomposition (split, answer each part, combine in code), 5/5. Not yet in the copilot; planned for Day 16

## F4: Hid a conflict and cited a fact to the wrong page
- **Prompt version:** grounded_v1
- **Question:** How often do bank feeds sync?
- **Evidence given:** bank-reconciliation/bank-feed-faq (old), bank-reconciliation/bank-feed-sync (current)
- **What happened:** "Before version 2.3.0, connected bank feeds synced once a day [bank-reconciliation/bank-feed-faq]." The FAQ never mentions 2.3.0; that detail came from bank-feed-sync. Never said the pages disagree
- **Expected:** say the docs disagree, give each claim with its own citation, say which page is current
- **Cause:** model merged two disagreeing sources into one smooth story
- **Category:** hallucination (wrong attribution) + hidden conflict
- **Why it matters:** the rule-based check passed it; only reading the answer caught it
- **Status:** fixed in grounded_v2 (conflict rule + one fake example), 5/5

## F5: Missing spaces between words
- **Status:** CLOSED. Not a real defect. Display/copy artifact.
- **Evidence:** "timeskipped" appeared in copied output, but `'timeskipped' in d['text']` returned False
  (pypdf 6.18.1). The same thing appeared in parser output from local HTML ("anddo"),
  where the source has the space.
- **Lesson:** check the actual data with one direct test before blaming a component.
  Copied terminal output is not the data.

## F6: Copied the few-shot example and cited a judgment to a source
- **Prompt version:** grounded_v2
- **Question:** How often do bank feeds sync?
- **Evidence given:** bank-feed-faq, bank-feed-sync
- **What happened:** "Note: an older FAQ still says they sync once a day [bank-reconciliation/bank-feed-faq]; that page appears out of date [bank-reconciliation/bank-feed-sync]." Almost word for word the example in the prompt. And "appears out of date" is the model's own judgment, but it is cited to bank-feed-sync as if that page said it
- **Expected:** the conflict flagged in its own words; citations only on facts the page states
- **Cause:** few-shot examples are copied strongly; the citation rule doesn't cover conclusions
- **Category:** format / wrong attribution
- **Fix idea:** add a rule: "Never cite your own conclusions; cite only what a block says"
- **Status:** open (harmless here, but watch for it)

## F7: "not_covered" just repeats the question
- **Prompt version:** grounded_v2
- **Question:** What is the API rate limit on the Professional plan? (empty evidence)
- **What happened:** not_covered = "What is the API rate limit on the Professional plan?". v1 gave a useful explanation instead
- **Expected:** a short note on what is missing
- **Cause:** side effect of the v2 rewrite
- **Category:** style regression
- **Status:** open (minor)

## N1: A single-run "failure" that was noise
- **Prompt version:** grounded_v2
- **Question:** Since 2.3.1 fixed the multi-currency auto-match bug, can customers rely on auto-match for EUR again?
- **What happened:** failed once (didn't say "open", dropped the workaround). With 5 runs it passed 5/5
- **Lesson:** one run proves nothing. Compare prompts on several runs and report pass rates

## K1: Answer key fixes (not model failures)
- **Date:** Day 2, seed run with perfect retrieval
- **c2-06** "Has BUG-2310-02 been fixed yet?": must_include was "25", but the question only asks whether it's fixed. The model's answer ("No, it's open, affecting 2.3.1") was complete. Changed to "open"
- **c3-05** "Can a Starter customer design their own invoice template?": must_include was "3 standard", an extra detail. The model's answer ("No, custom templates are Professional and Enterprise only") was complete. Changed to "Professional"
- **Rule:** must_include tests the core fact the question asks for, nothing more
- **Result after fix:** 25/25 with perfect retrieval

## R1: Embedding confuses near-identical bug IDs
- **Query:** Is BUG-2310-02 fixed?
- **Result:** BUG-2310-01 ranked #1 (0.743), BUG-2310-02 #2 (0.740). Gap 0.003
- **Cause:** embeddings capture meaning; one changed character barely moves the vector
- **Category:** retrieval, exact token
- **Fix idea:** BM25 keyword search fused with vector search (Day 7)
- **Status:** open


## R2: Table header lost across chunks (predicted)
- **Strategy:** fixed-500
- **Where:** account-billing/plans-and-limits#1, #2; release-notes/v2.3.1#2
- **What:** rows without the header row, so plan names / column names are gone
- **Risk:** tier-gated answers can't tell which plan a value belongs to
- **Fix idea:** structure-aware chunking that keeps tables whole or repeats the header (Day 5)
- **Status:** open, waiting for baseline results to confirm

## F8: Incomplete answer, key fact left out
- **Question:** What kind of support does an Enterprise customer get? (h-06)
- **Retrieved:** support/contact-support#0 (rank 1, full table with header)
- **What happened:** listed channels and named CSM but left out the 4-hour response target
- **Cause:** not retrieval (the fact was in the top chunk); the model summarized too much
- **Status:** open. Watch whether it repeats across runs before changing the prompt

## F9: Citation in text but not in the citation list
- **Question:** Did bank feeds sync every 4 hours for a customer on 2.2.0? (h-08)
- **What happened:** "[bank-reconciliation/bank-feed-faq#0]" appears in the answer text
  but not in the citations field. The chunk WAS retrieved (rank 4), so not fabricated
- **Also:** the sentence copies the grounded_v2 example wording (see F6)
- **Status:** open, minor. A Day 11 check can fix the list from the text automatically

## K3: Answer key fixes
- c1-01: must_include "pay online" -> "online" (answer said "pay invoices online")
- h-07: must_include "2.3.1" -> "local" (question asks about 2.3.0; "local time" is the core fact)
- Rule (same as K1): must_include tests the core fact the question asks for