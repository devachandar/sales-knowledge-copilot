---
title: Postmortem INC-2026-019: Auto-match fails on multi-currency accounts
doc_type: postmortem
audience: internal
owner: platform-team
status: final
last_updated: 2026-08-25
related_bugs: [BUG-2310-01]
---

# Postmortem INC-2026-019: Auto-match fails on multi-currency accounts

**Incident:** INC-2026-019
**Bug:** BUG-2310-01 (Critical)
**Affected version:** 2.3.1
**Fixed in:** not yet fixed

## Impact
Every organization with a foreign-currency bank account on 2.3.1. Critical severity.

## Root cause
In 2.3.1 the matching service was moved to a new amount comparator that skips the currency conversion step. Foreign-currency transactions are compared in their own currency against base-currency invoices.

## Resolution
Workaround published: manual matching for foreign-currency transactions. The fix needs the comparator to load daily rates; see the planning note.

## Customer communication
Support linked affected tickets to BUG-2310-01. Customers get an email when the fix ships.
