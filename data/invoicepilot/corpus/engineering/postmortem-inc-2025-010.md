---
title: Postmortem INC-2025-010: JPY invoice totals rounded wrong
doc_type: postmortem
audience: internal
owner: platform-team
status: final
last_updated: 2025-06-22
related_bugs: [BUG-2000-01]
---

# Postmortem INC-2025-010: JPY invoice totals rounded wrong

**Incident:** INC-2025-010
**Bug:** BUG-2000-01 (High)
**Affected version:** 2.0.0
**Fixed in:** 2.1.0

## Impact
Up to 1 yen per line item overcharged.

## Root cause
Line totals were rounded to 2 decimals before summing, which is wrong for zero-decimal currencies like JPY and KRW.

## Resolution
Round per currency's minor units. Fixed in 2.1.0. Finance issued credits to affected customers.

## Customer communication
Support linked affected tickets to BUG-2000-01. Customers get an email when the fix ships.
