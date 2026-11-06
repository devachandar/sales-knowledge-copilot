---
title: Postmortem INC-2026-004: Safari client portal login loop
doc_type: postmortem
audience: internal
owner: platform-team
status: final
last_updated: 2026-01-25
related_bugs: [BUG-2200-01]
---

# Postmortem INC-2026-004: Safari client portal login loop

**Incident:** INC-2026-004
**Bug:** BUG-2200-01 (Medium)
**Affected version:** 2.2.0
**Fixed in:** 2.2.0

## Impact
About 9% of portal sign-ins failed for 2 days.

## Root cause
The new portal session cookie was set with SameSite=Strict. Safari dropped it on the redirect from the sign-in page, so users were sent back to sign in.

## Resolution
Changed the cookie to SameSite=Lax and redeployed within 2.2.0 on 2026-01-27.

## Customer communication
Support linked affected tickets to BUG-2200-01. Customers get an email when the fix ships.
