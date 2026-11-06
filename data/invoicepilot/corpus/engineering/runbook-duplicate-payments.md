---
title: Runbook: cleaning up duplicate API payments
doc_type: runbook
audience: internal
owner: support-eng
status: final
last_updated: 2026-04-10
---

# Runbook: cleaning up duplicate API payments

1. Run the duplicate-payments report for the organization.
2. Confirm with the customer which payment to keep.
3. Delete the duplicate with DELETE /v2/payments/{payment_id}. The invoice reopens and then closes again when the right payment is applied.
