---
title: Postmortem INC-2026-011: Duplicate payments from API retries
doc_type: postmortem
audience: internal
owner: platform-team
status: final
last_updated: 2026-04-06
related_bugs: [BUG-2210-02]
---

# Postmortem INC-2026-011: Duplicate payments from API retries

**Incident:** INC-2026-011
**Bug:** BUG-2210-02 (High)
**Affected version:** 2.2.1
**Fixed in:** 2.3.0

## Impact
214 duplicate payments across 9 API customers.

## Root cause
A refactor of the payments service in 2.2.1 moved the payment write before the idempotency check. Retries with the same Idempotency-Key created a second payment.

## Resolution
Restored the check order and added a test for every POST endpoint. Fixed in 2.3.0. A script found and listed 214 duplicate payments for support.

## Customer communication
Support linked affected tickets to BUG-2210-02. Customers get an email when the fix ships.
