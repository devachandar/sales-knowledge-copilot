# InvoicePilot POC Dataset

A small, self-consistent synthetic dataset for a fictional invoicing/accounting
SaaS product called **InvoicePilot** (styled after products like Zoho Books).
Built for prototyping a RAG agent that grounds answers across sales data,
usage data, product documentation, and bug/issue data.

## Files

| File | Rows | What it is |
|---|---|---|
| `customers.csv` | 30 | Company accounts (includes "Oracle" as a running example) |
| `product_versions.csv` | 5 | Version metadata: version, codename, release date, summary |
| `sales_records.csv` | 220 | Orders / license events: new, renewal, upgrade, add seats |
| `usage_logs.csv` | 180 | Monthly usage per customer (Apr-Sep 2026): active seats, logins, features used |
| `bugs.csv` | 10 | Bug tracker records, tagged by affected/fixed version |
| `support_tickets.csv` | 40 | Support tickets, some linked to a `bug_id` |
| `docs/*.pdf` | 5 | Release-notes PDF per version, including a "Known Issues" section |

## How the tables link together

```
customers.customer_id
   |-- sales_records.customer_id      (what they bought, which version, license status)
   |-- usage_logs.customer_id         (how actively they're using it, month by month)
   \-- support_tickets.customer_id    (what they've reported)

product_versions.version
   |-- sales_records.product_version
   |-- usage_logs.product_version
   |-- bugs.affected_version / fixed_in_version
   |-- support_tickets.product_version
   \-- docs/InvoicePilot_Release_Notes_v<version>.pdf   (unstructured doc counterpart)

bugs.bug_id
   \-- support_tickets.linked_bug_id
```

## The built-in demo scenario (Oracle)

The dataset is deliberately seeded so the exact kind of question you described
has a real, groundable answer:

- `sales_records.csv`: Oracle (`CUST-0001`) has 5 orders, ending in an
  **Upgrade to version 2.3.1** on 2026-08-20, Enterprise plan, 260 seats,
  license status **Active**, expiring 2027-08-20.
- `usage_logs.csv`: Oracle's Jul/Aug/Sep 2026 rows show 230-255 active seats
  and steady logins — i.e. clearly active, legitimate usage this month.
- `docs/InvoicePilot_Release_Notes_v2.3.1.pdf`: lists **BUG-2310-01** ("Bank
  reconciliation auto-match fails for multi-currency accounts") as an open,
  Critical known issue in that exact version.
- `support_tickets.csv`: Oracle filed `TCKT-00040` on 2026-09-09 describing
  that exact problem, linked to `BUG-2310-01`.

So a query like *"Was Oracle sold version 2.3.1, are they actively using it
this month, and is there a known bug in that version?"* can be answered by
joining `sales_records` + `usage_logs` (structured) with the PDF release
notes and `bugs.csv` (the documentation side) — a genuine multi-hop,
multi-source grounding case.

## Suggested ingestion split for a RAG/agent build

- **Structured / SQL or pandas side:** `customers.csv`, `sales_records.csv`,
  `usage_logs.csv`, `bugs.csv`, `support_tickets.csv` — query these directly
  rather than embedding them; an agent with a SQL or dataframe tool can
  answer "was it sold", "is the license active", "how many seats are active
  this month" precisely.
- **Retrieval / embedding side:** the 5 release-notes PDFs — chunk and embed
  these for the free-text "what changed in this version" / "is this a known
  issue" style questions.
- **The bridge:** `bugs.csv` and `support_tickets.csv` give you exact bug IDs
  and version numbers to use as filters or citations when grounding an answer
  that spans both sides.

## Scale

This is intentionally small (POC-sized, not production-scale): ~30 customers,
~220 sales records, ~180 usage rows, 10 bugs, 40 tickets, 5 documents. Every
number above is generated (`generate_data.py` / `generate_docs.py`, included
if you want to regenerate or scale it up later) — nothing here is real
company or transaction data.
