---
title: Postmortem INC-2026-016: Bank feed provider outage
doc_type: postmortem
audience: internal
owner: platform-team
status: final
last_updated: 2026-06-02
---

# Postmortem INC-2026-016: Bank feed provider outage

**Incident:** INC-2026-016
**Date:** 2026-06-01, 08:05 to 11:40 UTC

## Impact
Bank feed sync failed for US accounts using our main aggregator. API calls to bank endpoints returned HTTP 503 with IP-5030.

## Root cause
The aggregator had an outage. Our sync retried too fast and was throttled after they recovered.

## Resolution
Added jittered backoff to sync retries. IP-5030 is the correct code for this case and clients should retry with backoff.
