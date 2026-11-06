---
title: Runbook: customer endpoint disabled
doc_type: runbook
audience: internal
owner: support-eng
status: final
last_updated: 2026-08-01
---

# Runbook: customer endpoint disabled

1. Check the endpoint's delivery log for the first failure.
2. Endpoints are disabled after 3 days of failures; deliveries older than 24 hours are not retried.
3. Tell the customer to re-enable it and backfill with GET /v2/invoices?updated_since=.
