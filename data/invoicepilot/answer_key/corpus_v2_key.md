# Corpus v2 answer key

Do NOT ingest this file. Corpus v1's answer key (planted_conflicts.md) still applies.

## What v2 adds
- Releases: 1.8.0 "Harbor", 1.9.0 "Lighthouse" (InvoicePilot Classic), 2.0.1, 2.1.1, 2.2.1 (patches).
- 15 new bugs. The full list is in bugs_v2.csv. Every new bug is fixed or Won't Fix; the v1 open bugs (BUG-2300-01, BUG-2310-01/02/03) are still open.
- New plan fact: webhook endpoints, Starter none, Professional 5, Enterprise 25.
- New platform fact: 10 concurrent requests per API key on every plan (IP-4291).
- New error subcodes: IP-4041, IP-4091, IP-4221 to IP-4226, IP-4291, IP-5031.

## Conflicts planted in v2

| # | Topic | Stale / weak source | Authoritative source | Correct answer |
|---|---|---|---|---|
| 10 | Version list | support/version-history and support/known-issues (v1 pages) list only 2.0.0 to 2.3.1 and the v1 bugs | Release notes PDFs for 2.0.1, 2.1.1, 2.2.1; bugs_v2.csv | Patch releases exist; the v1 pages are incomplete |
| 11 | Bank feeds on Professional | sales/battlecard-ledgerloop-2025.docx (archived, says 5 feeds) | account-billing/plans-and-limits | 10 feeds on Professional |
| 12 | Bank feed sync | sales/battlecard-ledgerloop-2025.docx (says once a day) | bank-reconciliation/bank-feed-sync | Every 4 hours since 2.3.0 |
| 13 | Prices | sales/pricing-sheet-2025.docx (archived: $10/$22/$36) | sales/pricing-sheet-2026.docx, account-billing/change-plan | $12 / $25 / $40 per seat per year |
| 14 | Custom roles | sales/draft-roles-messaging.docx (draft, says Professional) | account-billing/roles-and-audit-log | Enterprise only |
| 15 | Webhook retries | community/webhook-retries-5 (says 5) | api/webhook-retries, engineering/adr-018 | 8 retries over 24 hours since 2026-07-20 |
| 16 | Bulk void limit | community/bulk-void-50 (says 50) | invoicing/bulk-invoice-actions | 100 |
| 17 | API v1 shutdown | community/api-v1-shutdown (rumor: end of 2026) | api/migrate-v1-to-v2 | No shutoff date; 12 months' notice |
| 18 | Fix dates for open bugs | engineering/planning-q4-2026-fixes.md (internal, tentative 2.4.0) and community/auto-match-gbp (rumor) | Public docs say nothing | Say there is no committed fix date. The internal note says not to share dates |
| 19 | Late fees | legacy/classic-late-fees (1.x) | invoicing/late-fees-in-2x | 2.x has no automatic late fees |
| 20 | Classic API rate limit | legacy/classic-api (30/min) | api/api-rate-limits | 60 / 300 / 1,000 by plan on 2.x |

## Support tickets with a wrong agent answer (low authority)

| Ticket | Scenario | What the agent wrongly said |
|---|---|---|
| TCKT-20124 | custom_roles | Yes, custom roles are available on Professional and Enterprise. Go to Settings > Roles. |
| TCKT-20129 | bulk_limit | Bulk actions are limited to 50 invoices at a time, so do it in batches of 50. |
| TCKT-20164 | seat_proration | Yes, added seats are prorated to your next renewal date. |

## v1 questions whose answer grows in v2
- h-15 (which API errors to retry): v2 adds retryable subcodes IP-4091 (after 1 second), IP-4291 (after Retry-After), and IP-5031 (with backoff), on api/api-error-subcodes.
- Questions about "every release" or "all known bugs" now need the patch releases and bugs_v2.csv.

## Facts still NOT in the public docs
- A shutoff date for API v1
- A committed fix date for BUG-2310-01/02/03 or BUG-2300-01 (only an internal tentative target exists)
- SSO/SAML timelines
- Any customer's discount (the general discount policy is in sales/discount-policy.docx)
