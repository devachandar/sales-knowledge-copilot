# Answer key: planted conflicts and data mismatches

Do NOT ingest this file. It lists the right answers for your conflict and
data-quality tests (Day 18 and the golden set).

## Conflicts planted in the help center

| # | Topic | Stale / weak source | Authoritative source | Correct answer |
|---|---|---|---|---|
| 1 | Recurring invoice time zone | recurring-invoices/recurring-schedule-local-time (2025-10-12, says local time) | recurring-invoices/recurring-invoice-timezones (2026-08-14) | Since 2.3.1, schedules are calculated in UTC; shown in local time |
| 2 | Bank feed sync frequency | bank-reconciliation/bank-feed-faq (2025-11-04, says once a day) | bank-reconciliation/bank-feed-sync (2026-05-11) | Every 4 hours since 2.3.0; once a day before |
| 3 | Which API to use | api/api-quickstart-2025 (2025-07-14, says v1 is recommended) | api/api-overview (2026-01-20) | v2 is current; v1 is legacy but still works |
| 4 | Bulk action limit | community/bulk-send-tips (community, says 50) | invoicing/bulk-invoice-actions (official, says 100) | 100 invoices per bulk action |

## Conflicts that came with the original data package

| # | Where | What disagrees | Correct handling |
|---|---|---|---|
| 5 | Release notes v2.1.0 PDF | Upgrade notes say "see Known Issues below for a daylight-saving edge case", but the Known Issues table only lists BUG-2100-01. bugs.csv shows BUG-2100-02 (DST) affected 2.1.0 | Answer from bugs.csv: BUG-2100-02 affected 2.1.0, fixed in 2.3.1. Mention the PDF omits it |
| 6 | usage_logs.csv, Oracle 2026-07 | seats_licensed = 260 in July, but the order raising Oracle to 260 seats (SALE-00226) is dated 2026-08-20 | Flag the mismatch; trust the sales record for when seats were bought |
| 7 | sales_records.csv vs release notes 2.3.1 | Release notes and how-updates-roll-out say patches roll out automatically, but Oracle has a paid Upgrade order to 2.3.1 (SALE-00226) | Flag it; the order may really be the seat increase recorded on a 2.3.1 line |
| 8 | usage_logs.csv | 6 rows show recurring_invoices used on 2.0.0; the feature arrived in 2.1.0 | Flag as a data error; do not claim recurring invoices existed in 2.0.0 |
| 9 | Time | usage_logs.csv ends at 2026-09. Questions about "this month" in October 2026 have no data | Say the latest data is September 2026; do not silently answer with September |

## Facts that are deliberately NOT in the docs (should get "not in the documentation")

- A shutoff date for API v1 (docs say there is none yet)
- When BUG-2310-01, BUG-2310-02, or BUG-2310-03 will be fixed
- SSO/SAML timelines
- Any customer's discount or contract terms
