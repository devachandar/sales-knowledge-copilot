"""
Corpus v2: grow the InvoicePilot corpus from 74 documents to about 500.

Usage (run from data/invoicepilot/):
    pip install reportlab python-docx
    python generate_corpus_v2.py --data data_package --out corpus --key answer_key

It only ADDS files. Nothing from corpus v1 is changed or deleted.

Writes:
    corpus/release_notes/InvoicePilot_Release_Notes_v{1.8.0,1.9.0,2.0.1,2.1.1,2.2.1}.pdf
    corpus/help_center/api/*.html            more endpoints, webhooks, SDKs, error subcodes, changelog
    corpus/help_center/<section>/*.html      deeper how-tos and troubleshooting pages
    corpus/help_center/legacy/*.html         InvoicePilot Classic (1.x) pages, kept online but stale
    corpus/help_center/community/*.html      more forum posts (low authority)
    corpus/support_tickets/TCKT-2xxxx.json   ticket threads exported from the helpdesk
    corpus/engineering/*.md                  internal postmortems, design notes, runbooks
    corpus/sales/*.docx                      sales enablement: battlecards, pricing, objections
    answer_key/corpus_v2_key.md              NEVER ingest: planted conflicts and new facts
    answer_key/bugs_v2.csv                   NEVER ingest: every bug, v1 + v2

Design rules (same spirit as v1):
  * v1 facts stay true. New docs add facts; they never change an existing answer,
    except where a conflict is planted on purpose and listed in the answer key.
  * New look-alike tokens on purpose: BUG-2100-03 vs BUG-2110-01, IP-4220 vs IP-4221,
    X-InvoicePilot-Signature vs X-InvoicePilot-Timestamp, client.invoices.void vs .send.
  * The same token now appears in many places (tickets, postmortems, notes, forum),
    so search has to choose between them.
  * Formats: HTML, PDF, JSON, Markdown with YAML front matter, DOCX.
"""

import argparse
import csv
import html
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

random.seed(7)
TODAY = date(2026, 11, 3)

# ---------------------------------------------------------------------------
# New releases and bugs. v1 had 2.0.0, 2.1.0, 2.2.0, 2.3.0, 2.3.1.
# Bug IDs follow the v1 rule: BUG-<affected version digits><0>-<nn>.
# ---------------------------------------------------------------------------

NEW_VERSIONS = [
    # version, codename, release date, summary
    ("1.8.0", "Harbor", "2024-09-10", "InvoicePilot Classic: late fees, CSV export, and faster reports."),
    ("1.9.0", "Lighthouse", "2025-01-14", "InvoicePilot Classic: estimates, attachments, and the last 1.x release."),
    ("2.0.1", "Nova Patch 1", "2025-07-15", "Patch release fixing exchange-rate refresh and invoice numbering."),
    ("2.1.1", "Solstice Patch 1", "2025-11-03", "Patch release fixing duplicate payment reminders and receipt rotation."),
    ("2.2.1", "Meridian Patch 1", "2026-03-10", "Patch release fixing API v2 pagination and bulk void reminders."),
]

ALL_RELEASES = [  # every release, oldest first, for picking "the version a customer was on"
    ("1.8.0", "2024-09-10"), ("1.9.0", "2025-01-14"), ("2.0.0", "2025-06-10"), ("2.0.1", "2025-07-15"),
    ("2.1.0", "2025-09-16"), ("2.1.1", "2025-11-03"), ("2.2.0", "2026-01-20"), ("2.2.1", "2026-03-10"),
    ("2.3.0", "2026-05-11"), ("2.3.1", "2026-08-14"),
]

NEW_BUGS = [
    # bug_id, title, affected, fixed_in, severity, status, reported, description
    ("BUG-1800-01", "CSV export uses semicolons as separators in some locales", "1.8.0", "1.9.0", "Low", "Fixed", "2024-10-02",
     "Organizations with a German or French locale got CSV exports separated by semicolons instead of commas."),
    ("BUG-1800-02", "Late fees calculated on the tax amount", "1.8.0", "1.9.0", "High", "Fixed", "2024-10-21",
     "Late fees were calculated on the invoice total including tax instead of the subtotal, overcharging clients."),
    ("BUG-1900-01", "Invoice emails with attachments delayed up to 2 hours", "1.9.0", "", "Medium", "Won't Fix", "2025-02-11",
     "Invoice emails with attachments larger than 5 MB were queued and could arrive up to 2 hours late. Superseded by the 2.0.0 email service."),
    ("BUG-1900-02", "Reports time out above 5,000 invoices", "1.9.0", "2.0.0", "Medium", "Fixed", "2025-03-04",
     "Standard reports for organizations with more than 5,000 invoices timed out after 60 seconds."),
    ("BUG-2000-03", "Exchange rates not refreshed on weekends", "2.0.0", "2.0.1", "Medium", "Fixed", "2025-06-21",
     "Daily exchange rates were not refreshed on Saturdays and Sundays, so weekend invoices used Friday's rate."),
    ("BUG-2000-04", "Invoice numbering skips a number after a draft is deleted", "2.0.0", "2.0.1", "Low", "Fixed", "2025-06-30",
     "Deleting a draft invoice consumed its number, leaving a gap in the INV- sequence."),
    ("BUG-2010-01", "Archived tax rates hidden on existing drafts", "2.0.1", "2.1.0", "Low", "Fixed", "2025-08-05",
     "Draft invoices that used a tax rate archived later showed an empty tax field instead of the archived rate."),
    ("BUG-2100-03", "Receipt scanning rotates landscape receipts", "2.1.0", "2.1.1", "Low", "Fixed", "2025-09-29",
     "Receipts photographed in landscape were rotated 90 degrees before OCR, so the amount was often missed."),
    ("BUG-2100-04", "Payment reminder sent twice when the send window crosses midnight", "2.1.0", "2.1.1", "Medium", "Fixed", "2025-10-14",
     "Client-level reminders with a send window that crossed midnight UTC were sent twice."),
    ("BUG-2110-01", "Recurring invoice preview shows the wrong currency symbol", "2.1.1", "2.2.0", "Low", "Fixed", "2025-11-20",
     "The preview of upcoming recurring invoices showed the base currency symbol for clients billed in another currency. The invoices themselves were correct."),
    ("BUG-2110-02", "Expense CSV import rejects DD/MM/YYYY dates", "2.1.1", "2.2.1", "Medium", "Fixed", "2025-12-02",
     "Importing expenses from CSV failed for files with dates written as DD/MM/YYYY."),
    ("BUG-2200-03", "Bulk void leaves payment reminders scheduled", "2.2.0", "2.2.1", "Medium", "Fixed", "2026-02-09",
     "Invoices voided with a bulk action kept their scheduled payment reminders, so clients got reminders for void invoices."),
    ("BUG-2200-04", "API v2 list endpoints return next_cursor on the last page", "2.2.0", "2.2.1", "Medium", "Fixed", "2026-02-17",
     "List endpoints returned a non-null next_cursor on the last page, so integrations made one extra empty request."),
    ("BUG-2210-01", "Portal Pay now button hidden for partially paid invoices", "2.2.1", "2.3.0", "High", "Fixed", "2026-03-24",
     "Clients could not pay the rest of a partially paid invoice from the client portal because the Pay now button was hidden."),
    ("BUG-2210-02", "Idempotency-Key ignored on POST /v2/payments", "2.2.1", "2.3.0", "High", "Fixed", "2026-04-06",
     "Retries of POST /v2/payments with the same Idempotency-Key created duplicate payments. Other endpoints were not affected."),
]

PATCH_COPY = {
    "1.8.0": dict(headline="InvoicePilot Classic adds late fees, CSV export, and faster reports.",
                  new=["Late fees: add a fixed or percentage fee to overdue invoices automatically.",
                       "CSV export for invoices, payments, and expenses.",
                       "Standard reports load up to 3x faster."],
                  imp=["Invoice emails can include a custom message.", "Expense categories can be renamed."],
                  upgrade="1.8.0 rolls out to all Classic organizations. Late fees are off by default; turn them on under Settings > Late Fees."),
    "1.9.0": dict(headline="InvoicePilot Classic adds estimates and attachments. This is the last 1.x release.",
                  new=["Estimates: send a quote and convert it to an invoice.",
                       "Attach files up to 10 MB to invoices.",
                       "Two-step verification for sign-in."],
                  imp=["Late fees are now calculated on the subtotal, not the total.", "CSV exports always use commas."],
                  upgrade="1.9.0 is the final Classic release. InvoicePilot 2.0.0 replaces Classic in 2025; Classic organizations will be moved to 2.0.0 automatically."),
    "2.0.1": dict(headline="Patch release: exchange-rate refresh and invoice numbering fixes.",
                  new=[], imp=["Exchange rates now refresh every day, including weekends.",
                               "Deleting a draft no longer consumes an invoice number."],
                  upgrade="This is a patch release. It is rolled out automatically to all organizations on the 2.0.x line."),
    "2.1.1": dict(headline="Patch release: duplicate reminders and receipt rotation fixes.",
                  new=[], imp=["Payment reminders are sent once even when the send window crosses midnight.",
                               "Receipt scanning detects landscape photos and rotates them correctly."],
                  upgrade="This is a patch release. It is rolled out automatically to all organizations on the 2.1.x line."),
    "2.2.1": dict(headline="Patch release: API v2 pagination and bulk void reminder fixes.",
                  new=[], imp=["API v2 list endpoints now return next_cursor: null on the last page.",
                               "Voiding invoices in bulk now cancels their scheduled payment reminders.",
                               "Expense CSV import accepts DD/MM/YYYY and YYYY-MM-DD dates."],
                  upgrade="This is a patch release. It is rolled out automatically to all organizations on the 2.2.x line. "
                          "No API changes are needed; integrations that stopped on an empty last page keep working."),
}

PLANS = ["Starter", "Professional", "Enterprise"]
PRO_UP = ["Professional", "Enterprise"]

SECTION_NAMES = {
    "getting-started": "Getting Started", "invoicing": "Invoicing", "multi-currency": "Multi-Currency",
    "recurring-invoices": "Recurring Invoices", "expenses": "Expenses", "estimates": "Estimates",
    "client-portal": "Client Portal", "bank-reconciliation": "Bank Reconciliation", "reports": "Reports",
    "account-billing": "Account & Billing", "api": "Developer API", "support": "Support",
    "community": "Community", "legacy": "InvoicePilot Classic (1.x)",
}
NAV = " | ".join(SECTION_NAMES[s] for s in SECTION_NAMES if s not in ("community", "legacy"))

# ---------------------------------------------------------------------------
# HTML rendering, identical to v1 so the v1 parser works unchanged
# ---------------------------------------------------------------------------

def esc(t):
    return html.escape(t, quote=False)


def render_blocks(blocks):
    out = []
    for b in blocks:
        k = b[0]
        if k == "p":
            out.append(f"<p>{esc(b[1])}</p>")
        elif k in ("h2", "h3"):
            out.append(f"<{k}>{esc(b[1])}</{k}>")
        elif k in ("ul", "ol"):
            out.append(f"<{k}>" + "".join(f"<li>{esc(i)}</li>" for i in b[1]) + f"</{k}>")
        elif k == "table":
            head = "".join(f"<th>{esc(h)}</th>" for h in b[1])
            body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in b[2])
            out.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
        elif k == "code":
            out.append(f"<pre><code>{esc(b[1])}</code></pre>")
        elif k == "note":
            out.append(f'<div class="callout note"><strong>Note:</strong> {esc(b[1])}</div>')
        elif k == "warn":
            out.append(f'<div class="callout warning"><strong>Known issue:</strong> {esc(b[1])}</div>')
        else:
            raise ValueError(k)
    return "\n".join(out)


FOOTER = ('<footer><p>&copy; 2026 InvoicePilot, Inc. All rights reserved. <a href="/privacy">Privacy</a> · '
          '<a href="/terms">Terms</a> · <a href="/status">Status</a></p><div class="cookie-banner">We use cookies to '
          'improve your experience. <button>Accept all</button> <button>Manage preferences</button></div></footer>')


def render_page(a):
    meta = [f'<meta name="doc-id" content="{a["id"]}">']
    community = a["type"] == "community"
    if not community:
        meta.append(f'<meta name="source-type" content="{a["type"]}">')
        meta.append(f'<meta name="last-updated" content="{a["updated"]}">')
        if a.get("applies"):
            meta.append(f'<meta name="applies-to-version" content="{a["applies"]}">')
        if a.get("plans"):
            meta.append(f'<meta name="available-on-plans" content="{", ".join(a["plans"])}">')
    bits = []
    if community:
        bits.append(f'<p class="byline">Posted by {esc(a["author"])} on {a["updated"]} · Community answer, not reviewed by InvoicePilot staff</p>')
    else:
        bits.append(f'<p class="updated">Last updated: {a["updated"]}</p>')
        if a.get("applies"):
            bits.append(f'<p class="applies">Applies to: InvoicePilot {esc(a["applies"])}</p>')
        if a.get("plans"):
            bits.append(f'<p class="plans">Available on: {esc(", ".join(a["plans"]))}</p>')
    related = ""
    if a.get("related"):
        links = "".join(f'<li><a href="{r}.html">{r}</a></li>' for r in a["related"])
        related = f'<aside class="related"><h4>Related articles</h4><ul>{links}</ul></aside>'
    helpful = random.randint(12, 2400)
    feedback = ("" if community else
                f'<div class="feedback">Was this article helpful? <button>Yes</button> <button>No</button> '
                f'<span>{helpful:,} people found this helpful</span></div>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{esc(a["title"])} | InvoicePilot Help Center</title>
{chr(10).join(meta)}
</head>
<body>
<header><div class="logo">InvoicePilot</div><nav class="top">{esc(NAV)}</nav>
<form class="search"><input placeholder="Search the help center"></form></header>
<nav class="breadcrumb">Help Center &gt; {esc(SECTION_NAMES[a["section"]])} &gt; {esc(a["title"])}</nav>
<main>
<article>
<h1>{esc(a["title"])}</h1>
{chr(10).join(bits)}
{render_blocks(a["body"])}
</article>
{related}
{feedback}
</main>
{FOOTER}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Help center: API reference (new endpoints, webhooks, SDKs, subcodes, changelog)
# ---------------------------------------------------------------------------

def api_pages(art):
    def endpoint(slug, title, added, rows, extra=None, applies="2.2.0+", plans=PLANS, related=None):
        body = [("p", f"Added to API v2 on {added}. See the API changelog."),
                ("table", ["Method", "Path", "Does"], rows)]
        body += extra or []
        art("api", slug, title, added, body, type="api_reference", applies=applies, plans=plans,
            related=related or ["api-overview", "api-errors"])

    endpoint("api-estimates", "Estimates endpoint", "2026-04-02", [
        ["GET", "/v2/estimates", "List estimates. Filters: status, customer_id"],
        ["POST", "/v2/estimates", "Create an estimate"],
        ["GET", "/v2/estimates/{estimate_id}", "Get one estimate"],
        ["POST", "/v2/estimates/{estimate_id}/send", "Email the estimate"],
        ["POST", "/v2/estimates/{estimate_id}/convert", "Convert an accepted estimate to an invoice"]],
        [("p", "Converting an estimate that is not accepted returns HTTP 422 with IP-4225.")])
    endpoint("api-expenses", "Expenses endpoint", "2026-04-02", [
        ["GET", "/v2/expenses", "List expenses. Filters: category_id, date_from, date_to"],
        ["POST", "/v2/expenses", "Record an expense"],
        ["POST", "/v2/expenses/{expense_id}/receipt", "Upload a receipt image (JPEG, PNG, or PDF, up to 10 MB)"],
        ["DELETE", "/v2/expenses/{expense_id}", "Delete an expense"]],
        [("p", "Receipts uploaded through the API are scanned the same way as receipts uploaded in the app.")])
    endpoint("api-bank-transactions", "Bank transactions endpoint", "2026-06-15", [
        ["GET", "/v2/bank_accounts", "List connected bank accounts"],
        ["GET", "/v2/bank_transactions", "List transactions. Filters: bank_account_id, status=unmatched|matched"],
        ["POST", "/v2/bank_transactions/{transaction_id}/match", "Match a transaction to an invoice or expense"],
        ["POST", "/v2/bank_transactions/{transaction_id}/unmatch", "Undo a match (within 30 days)"]],
        [("note", "Matching through the API follows the same rules as the app. On 2.3.1, foreign-currency "
                  "transactions are not converted before auto-match compares amounts (BUG-2310-01), so match them explicitly.")],
        applies="2.3.0+", related=["auto-match", "api-errors"])
    endpoint("api-tax-rates", "Tax rates endpoint", "2026-04-02", [
        ["GET", "/v2/tax_rates", "List tax rates, including archived ones with archived=true"],
        ["POST", "/v2/tax_rates", "Create a tax rate"],
        ["POST", "/v2/tax_rates/{tax_rate_id}/archive", "Archive a tax rate. Existing invoices keep it"]])
    endpoint("api-recurring-profiles", "Recurring profiles endpoint", "2026-05-11", [
        ["GET", "/v2/recurring_profiles", "List recurring profiles"],
        ["POST", "/v2/recurring_profiles", "Create a recurring profile"],
        ["POST", "/v2/recurring_profiles/{profile_id}/pause", "Pause a profile. No invoices are generated while paused"],
        ["POST", "/v2/recurring_profiles/{profile_id}/resume", "Resume a profile from the next scheduled date"]],
        [("p", "next_run_at is returned in UTC. Since 2.3.1 schedules are calculated in UTC.")],
        related=["recurring-invoice-timezones", "api-errors"])
    endpoint("api-reports", "Reports endpoint", "2026-05-11", [
        ["GET", "/v2/reports", "List saved custom reports"],
        ["POST", "/v2/reports/{report_id}/run", "Run a saved report. Params: date_from, date_to, format=csv|xlsx|json"],
        ["GET", "/v2/report_runs/{run_id}", "Check a run and get its download link"]],
        [("p", "Report runs are asynchronous. Poll /v2/report_runs/{run_id} until status is complete."),
         ("warn", "BUG-2300-01 also affects the API: runs spanning more than 3 years fail. Split the range.")],
        applies="2.3.0+", plans=PLANS, related=["large-date-ranges", "custom-report-builder"])
    endpoint("api-users", "Users endpoint", "2026-07-01", [
        ["GET", "/v2/users", "List users and their roles"],
        ["POST", "/v2/users/invite", "Invite a user. The invite link expires after 7 days"],
        ["PATCH", "/v2/users/{user_id}", "Change a user's role"],
        ["DELETE", "/v2/users/{user_id}", "Remove a user and free the seat"]],
        [("p", "Assigning a custom role through the API needs Enterprise. On other plans, use Admin, Accountant, Staff, or Read-only.")])

    art("api", "webhooks-overview", "Webhooks overview", "2026-06-15", [
        ("p", "Webhooks send an HTTPS POST to your endpoint when something happens in InvoicePilot, so you do not have to poll the API."),
        ("table", ["Plan", "Webhook endpoints"], [["Starter", "Not available"], ["Professional", "5"], ["Enterprise", "25"]]),
        ("h2", "Set up an endpoint"),
        ("ol", ["Go to Settings > Developer > Webhooks, or call POST /v2/webhook_endpoints.",
                "Enter an HTTPS URL. Plain HTTP URLs are rejected with IP-4226.",
                "Choose the events to subscribe to.",
                "Copy the signing secret. It starts with whsec_ and is shown once."]),
        ("p", "Webhooks became generally available on 2026-06-15 for API v2."),
    ], type="api_reference", applies="2.3.0+", plans=PRO_UP, related=["webhook-events", "webhook-signatures", "webhook-retries"])
    events = [["invoice.created", "An invoice was created (draft or sent)"],
              ["invoice.sent", "An invoice was emailed or marked as sent"],
              ["invoice.viewed", "The client opened the invoice in the portal"],
              ["invoice.partially_paid", "A payment covered part of the invoice"],
              ["invoice.paid", "The invoice balance reached zero"],
              ["invoice.overdue", "The due date passed with a balance left"],
              ["invoice.voided", "The invoice was voided"],
              ["payment.created", "A payment was recorded, including portal payments"],
              ["payment.deleted", "A payment was deleted and its invoices reopened"],
              ["customer.created", "A customer was created"],
              ["customer.updated", "A customer's details changed"],
              ["estimate.accepted", "The client accepted an estimate"],
              ["estimate.declined", "The client declined an estimate"],
              ["recurring_invoice.generated", "A recurring profile generated an invoice"],
              ["bank_transaction.matched", "A bank transaction was matched, by auto-match or a person"]]
    art("api", "webhook-events", "Webhook event types", "2026-06-15", [
        ("p", "Every event has an id starting with evt_, a type, created_at in UTC, and a data object."),
        ("table", ["Event type", "Sent when"], events),
        ("code", '{\n  "id": "evt_1Q2w3E4r",\n  "type": "invoice.paid",\n  "created_at": "2026-07-02T14:05:11Z",\n  "data": {"invoice_id": "inv_7731", "amount_paid": 1500.00, "currency": "EUR"}\n}'),
        ("note", "invoice.paid is not sent for voided invoices. Listen for invoice.voided instead."),
    ], type="api_reference", applies="2.3.0+", plans=PRO_UP, related=["webhooks-overview"])
    art("api", "webhook-signatures", "Verify webhook signatures", "2026-06-15", [
        ("p", "Every webhook request has two headers. Check both before trusting the body."),
        ("table", ["Header", "Contains"], [
            ["X-InvoicePilot-Signature", "HMAC-SHA256 of timestamp + '.' + raw body, hex-encoded, using your whsec_ secret"],
            ["X-InvoicePilot-Timestamp", "Unix time the request was signed"]]),
        ("p", "Reject requests whose timestamp is more than 5 minutes old. This stops replay attacks."),
        ("code", "import hmac, hashlib\n\nsigned = f\"{timestamp}.{raw_body}\".encode()\nexpected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()\nok = hmac.compare_digest(expected, signature_header)"),
        ("p", "The Python SDK does this for you: client.webhooks.verify_signature(payload, signature, timestamp, secret)."),
    ], type="api_reference", applies="2.3.0+", plans=PRO_UP, related=["webhooks-overview", "sdk-python"])
    art("api", "webhook-retries", "Webhook retries and failures", "2026-07-20", [
        ("p", "Your endpoint must return a 2xx status within 10 seconds. Anything else counts as a failure."),
        ("h2", "Retry schedule"),
        ("p", "Failed deliveries are retried up to 8 times over 24 hours with exponential backoff: after 1 minute, 5 minutes, 30 minutes, 1 hour, 2 hours, 4 hours, 8 hours, and 8 hours."),
        ("h2", "Disabled endpoints"),
        ("p", "If every delivery to an endpoint fails for 3 days, the endpoint is disabled and admins get an email. Re-enable it under Settings > Developer > Webhooks."),
        ("p", "Deliveries can arrive more than once and out of order. Use the event id to ignore duplicates."),
    ], type="api_reference", applies="2.3.0+", plans=PRO_UP, related=["webhooks-overview", "webhook-events"])

    art("api", "api-error-subcodes", "Error subcodes", "2026-07-01", [
        ("p", "Some errors have a more specific subcode. The HTTP status is the same as the main code on Error codes."),
        ("table", ["HTTP", "Code", "Meaning", "Retry?"], [
            ["404", "IP-4041", "The resource exists but belongs to another organization", "No"],
            ["409", "IP-4091", "A request with this Idempotency-Key is still being processed", "Yes, after 1 second"],
            ["422", "IP-4221", "Line item validation failed (quantity, rate, or tax)", "No"],
            ["422", "IP-4222", "The currency is not enabled for this organization", "No"],
            ["422", "IP-4223", "The customer is archived", "No"],
            ["422", "IP-4224", "The invoice is void and cannot be changed", "No"],
            ["422", "IP-4225", "The estimate is not accepted, so it cannot be converted", "No"],
            ["422", "IP-4226", "Webhook URL must use HTTPS", "No"],
            ["429", "IP-4291", "Too many concurrent requests (more than 10 in flight per key)", "Yes, after Retry-After"],
            ["503", "IP-5031", "Payment processor unavailable", "Yes, with backoff"]]),
        ("note", "Older integrations that only check the main code keep working: IP-4221 to IP-4226 are all HTTP 422 validation errors."),
    ], type="api_reference", applies="2.2.1+", plans=PLANS, related=["api-errors"])

    art("api", "api-concurrency-limits", "Concurrency limits", "2026-07-01", [
        ("p", "Besides the per-minute rate limit, each API key can have at most 10 requests in flight at once."),
        ("p", "An 11th parallel request gets HTTP 429 with IP-4291 and a Retry-After header. This is different from IP-4290, which means the per-minute limit was reached."),
        ("p", "The concurrency limit is the same on every plan. Per-minute limits are 60, 300, or 1,000 by plan."),
    ], type="api_reference", applies="2.2.1+", plans=PLANS, related=["api-rate-limits", "api-error-subcodes"])

    art("api", "sdk-python", "Python SDK", "2026-08-03", [
        ("p", "Install with pip install invoicepilot. The current version is 3.2.0 and it supports Python 3.9 and later."),
        ("code", 'from invoicepilot import Client\n\nclient = Client(api_key="ip_live_xxxx", max_retries=2)\ninv = client.invoices.create(customer_id="cus_8812", currency="EUR",\n                             line_items=[{"description": "Consulting", "quantity": 10, "rate": 150}],\n                             idempotency_key="7f9c2e1a")\nclient.invoices.send(inv.id)'),
        ("table", ["Method", "API call"], [
            ["client.invoices.create(...)", "POST /v2/invoices"],
            ["client.invoices.send(invoice_id)", "POST /v2/invoices/{invoice_id}/send"],
            ["client.invoices.void(invoice_id, reason=...)", "POST /v2/invoices/{invoice_id}/void"],
            ["client.payments.create(...)", "POST /v2/payments"],
            ["client.payments.delete(payment_id)", "DELETE /v2/payments/{payment_id}"],
            ["client.customers.get_statement(customer_id, format=\"json\")", "GET /v2/customers/{customer_id}/statements"],
            ["client.webhooks.verify_signature(payload, signature, timestamp, secret)", "Checks X-InvoicePilot-Signature locally"]]),
        ("h2", "Retries"),
        ("p", "The SDK retries IP-4290, IP-4291, IP-5000, and IP-5030 automatically with backoff, up to max_retries times (default 2). It never retries 4xx validation errors."),
        ("p", "List methods such as client.invoices.list() follow next_cursor for you. Use auto_paginate=False to get one page."),
    ], type="api_reference", applies="2.2.0+", plans=PLANS, related=["sdk-node", "api-errors"])
    art("api", "sdk-node", "Node.js SDK", "2026-08-03", [
        ("p", "Install with npm install @invoicepilot/node. The current version is 2.4.1 and it supports Node 18 and later."),
        ("code", "import InvoicePilot from '@invoicepilot/node';\n\nconst ip = new InvoicePilot({ apiKey: process.env.IP_KEY, maxRetries: 2 });\nconst inv = await ip.invoices.create({ customerId: 'cus_8812', currency: 'EUR', lineItems: [...] },\n                                     { idempotencyKey: '7f9c2e1a' });\nawait ip.invoices.send(inv.id);"),
        ("p", "Method names match the Python SDK in camelCase: ip.invoices.void(), ip.payments.delete(), ip.customers.getStatement(), ip.webhooks.verifySignature()."),
        ("p", "Like the Python SDK, it retries 429, 500, and 503 errors automatically up to maxRetries (default 2)."),
    ], type="api_reference", applies="2.2.0+", plans=PLANS, related=["sdk-python"])
    art("api", "sandbox", "Sandbox environment", "2026-02-15", [
        ("p", "The sandbox is a separate copy of InvoicePilot for testing. Use keys that start with ip_test_."),
        ("ul", ["Base URL: https://sandbox.api.invoicepilot.example/v2",
                "Sandbox data is reset on the first day of every month",
                "Bank feeds in the sandbox use a fake bank called Test Bank with sample transactions",
                "Rate limits in the sandbox are 60 requests per minute on every plan",
                "Webhooks fire in the sandbox too"]),
    ], type="api_reference", applies="2.2.0+", plans=PLANS, related=["api-authentication"])
    art("api", "api-changelog", "API changelog", "2026-10-15", [
        ("p", "Changes to API v2, newest first. API changes are announced here and do not wait for app releases."),
        ("table", ["Date", "Change"], [
            ["2026-10-15", "GET /v2/invoices accepts updated_since for incremental sync"],
            ["2026-09-10", "Python SDK 3.2.0: auto_paginate option on list methods"],
            ["2026-08-03", "Node.js SDK 2.4.1 released"],
            ["2026-07-20", "Webhook retries extended from 5 to 8 attempts over 24 hours"],
            ["2026-07-01", "Users endpoint; error subcodes page published; concurrency limit of 10 documented"],
            ["2026-06-15", "Webhooks generally available; bank transactions endpoint"],
            ["2026-05-11", "Recurring profiles and reports endpoints; X-RateLimit-* headers on every response (fixes BUG-2200-02)"],
            ["2026-04-06", "Known issue: Idempotency-Key ignored on POST /v2/payments (BUG-2210-02), fixed in 2.3.0"],
            ["2026-04-02", "Estimates, expenses, and tax rates endpoints"],
            ["2026-03-10", "next_cursor is null on the last page (fixes BUG-2200-04)"],
            ["2026-02-15", "Sandbox environment"],
            ["2026-01-20", "API v2 released with invoices, customers, and payments"]]),
    ], type="api_reference", applies="2.2.0+", plans=PLANS, related=["api-overview"])


# ---------------------------------------------------------------------------
# Help center: more articles and troubleshooting pages
# ---------------------------------------------------------------------------

def help_pages(art, B):
    def ts(section, slug, title, bug_id, updated, steps, applies, related=None):
        b = B[bug_id]
        fixed = f"It was fixed in {b['fixed_in_version']}." if b["fixed_in_version"] else f"Status: {b['status']}."
        art(section, slug, title, updated, [
            ("p", f"{b['description']}"),
            ("p", f"This is {bug_id} ({b['severity']}). It affected {b['affected_version']}. {fixed}"),
            ("h2", "What to do"), ("ul", steps)],
            type="troubleshooting", applies=applies, plans=PLANS, related=related or ["known-issues"])

    ts("multi-currency", "weekend-exchange-rates", "Troubleshooting: weekend invoices used Friday's exchange rate",
       "BUG-2000-03", "2025-07-16", ["Update to 2.0.1 or later; this happens automatically.",
                                     "To fix an old invoice, edit the exchange rate on the invoice and save it."], "2.0.0")
    ts("invoicing", "invoice-number-gaps", "Troubleshooting: gaps in invoice numbers",
       "BUG-2000-04", "2025-07-16", ["Gaps created on 2.0.0 stay in the sequence; numbers are never reused.",
                                     "Since 2.0.1, deleting a draft frees its number.",
                                     "For auditors, export the Invoice Register report, which lists deleted drafts."], "2.0.0")
    ts("invoicing", "archived-tax-rate-drafts", "Troubleshooting: tax missing on an old draft",
       "BUG-2010-01", "2025-09-17", ["Open the draft and pick the tax rate again.", "Fixed in 2.1.0."], "2.0.1")
    ts("expenses", "receipt-rotated", "Troubleshooting: scanned receipt is sideways",
       "BUG-2100-03", "2025-11-04", ["Retake the photo in portrait mode, or update to 2.1.1.",
                                     "You can always type the amount by hand."], "2.1.0", ["receipt-scanning"])
    ts("invoicing", "duplicate-payment-reminders", "Troubleshooting: clients got the same reminder twice",
       "BUG-2100-04", "2025-11-04", ["Update to 2.1.1; this happens automatically.",
                                     "On 2.1.0, set the reminder send window so it does not cross midnight UTC."], "2.1.0",
       ["payment-reminders"])
    ts("recurring-invoices", "preview-currency-symbol", "Troubleshooting: recurring preview shows the wrong currency",
       "BUG-2110-01", "2026-01-21", ["Only the preview was wrong. Generated invoices used the right currency.",
                                     "Fixed in 2.2.0."], "2.1.1")
    ts("expenses", "expense-import-dates", "Troubleshooting: expense CSV import fails on dates",
       "BUG-2110-02", "2026-03-11", ["On 2.1.1 to 2.2.0, convert dates to YYYY-MM-DD before importing.",
                                     "Since 2.2.1, DD/MM/YYYY is accepted."], "2.1.1", ["record-an-expense"])
    ts("invoicing", "bulk-void-reminders", "Troubleshooting: reminders sent for voided invoices",
       "BUG-2200-03", "2026-03-11", ["On 2.2.0, cancel reminders by hand after a bulk void: open each client > Reminders.",
                                     "Since 2.2.1, a bulk void cancels reminders automatically."], "2.2.0",
       ["bulk-invoice-actions", "payment-reminders"])
    ts("client-portal", "portal-partial-payment", "Troubleshooting: client can't pay the rest of an invoice",
       "BUG-2210-01", "2026-05-12", ["On 2.2.1, send the client a payment link from the invoice: More > Copy payment link.",
                                     "Fixed in 2.3.0."], "2.2.1", ["partial-payments", "client-portal-overview"])
    ts("api", "duplicate-api-payments", "Troubleshooting: duplicate payments from API retries",
       "BUG-2210-02", "2026-05-12", ["On 2.2.1, check GET /v2/payments for an existing payment before retrying.",
                                     "Delete duplicates with DELETE /v2/payments/{payment_id}; the invoice reopens.",
                                     "Fixed in 2.3.0. Idempotency-Key now works on every POST endpoint."], "2.2.1",
       ["api-errors", "api-payments"])

    art("invoicing", "record-payment", "Record a payment", "2026-01-22", [
        ("p", "Record payments you receive outside the client portal, such as bank transfers or checks."),
        ("ol", ["Open the invoice and click Record Payment.", "Enter the amount, date, and method.",
                "Click Save. The invoice status changes to Paid or Partially paid."]),
        ("p", "Payments made through the client portal are recorded automatically."),
    ], applies="2.0.0+", plans=PLANS, related=["partial-payments", "refunds"])
    art("invoicing", "partial-payments", "Partial payments", "2026-05-12", [
        ("p", "An invoice can be paid in several parts. Each payment lowers the balance, and the status shows Partially paid until the balance is zero."),
        ("p", "Clients can pay the remaining balance from the client portal. On 2.2.1 the Pay now button was hidden for partially paid invoices (BUG-2210-01); this was fixed in 2.3.0."),
        ("p", "Payment reminders mention the remaining balance, not the original total."),
    ], applies="2.0.0+", plans=PLANS, related=["record-payment", "portal-partial-payment"])
    art("invoicing", "refunds", "Refund a payment", "2026-02-02", [
        ("p", "Refunds are recorded against a payment. The invoice is reopened for the refunded amount."),
        ("ol", ["Open the payment from the invoice.", "Click Refund and enter the amount.",
                "Choose whether to issue a credit note instead of reopening the invoice."]),
        ("p", "Refunds of portal card payments go back to the client's card within 5 to 10 business days."),
    ], applies="2.2.0+", plans=PLANS, related=["credit-notes", "record-payment"])
    art("invoicing", "credit-notes", "Credit notes", "2026-02-02", [
        ("p", "A credit note reduces what a client owes without deleting or voiding an invoice. Credit note numbers start with CN-."),
        ("ul", ["Apply a credit note to one or more open invoices",
                "Or keep it as client credit for future invoices",
                "Credit notes appear on customer statements"]),
        ("p", "Credit notes were added in 2.2.0 and are available on every plan."),
    ], applies="2.2.0+", plans=PLANS, related=["refunds", "void-or-delete-invoice"])
    art("invoicing", "invoice-numbering", "Invoice numbering", "2025-07-16", [
        ("p", "Invoices are numbered INV-000001, INV-000002, and so on. You can change the prefix and the next number under Settings > Invoices."),
        ("p", "Numbers are never reused, even if an invoice is voided."),
        ("p", "On 2.0.0, deleting a draft left a gap in the sequence (BUG-2000-04). Since 2.0.1, deleting a draft frees its number."),
    ], applies="2.0.0+", plans=PLANS, related=["invoice-number-gaps"])
    art("invoicing", "duplicate-invoice", "Duplicate an invoice", "2025-06-18", [
        ("p", "Open an invoice and click More > Duplicate. The copy is a new draft with today's date and the next number."),
        ("p", "To bill the same thing every month, set up a recurring invoice instead."),
    ], applies="2.0.0+", plans=PLANS, related=["set-up-recurring-invoices"])
    art("invoicing", "invoice-attachments", "Attach files to invoices", "2025-06-18", [
        ("p", "Attach up to 5 files per invoice, each up to 10 MB. Clients can download them from the email or the portal."),
        ("p", "Supported formats: PDF, PNG, JPEG, DOCX, XLSX, and CSV."),
    ], applies="2.0.0+", plans=PLANS)
    art("invoicing", "line-item-discounts", "Discounts on line items", "2025-06-18", [
        ("p", "Each line item can have a discount as a percentage or a fixed amount. Discounts are applied before tax."),
        ("p", "To discount the whole invoice, add a discount on every line or add a negative line item."),
    ], applies="2.0.0+", plans=PLANS)
    art("invoicing", "send-invoice-email", "Send invoices by email", "2026-01-22", [
        ("p", "When you send an invoice, the client gets an email with a link to view and pay it, plus the PDF attached."),
        ("ul", ["Edit the default email under Settings > Emails",
                "Add CC and BCC addresses per client",
                "See when the client opened the invoice in its activity log"]),
        ("p", "For invoices with more than 25 line items on 2.3.1, send the link rather than relying on the PDF (BUG-2310-02)."),
    ], applies="2.0.0+", plans=PLANS, related=["line-items-and-long-invoices", "create-invoice"])
    art("invoicing", "late-fees-in-2x", "Do late fees exist in InvoicePilot 2.x?", "2025-06-12", [
        ("p", "Automatic late fees were part of InvoicePilot Classic (1.x). They were not carried over to 2.0.0."),
        ("p", "In 2.x, add a late fee as a separate line item or a new invoice. Payment reminders can mention your late-fee terms."),
    ], type="faq", applies="2.0.0+", plans=PLANS, related=["payment-reminders"])
    art("recurring-invoices", "pause-recurring-invoice", "Pause or stop a recurring invoice", "2026-05-12", [
        ("p", "Open the recurring profile and click Pause. No invoices are generated while it is paused."),
        ("p", "When you resume, the next invoice goes out on the next scheduled date. Missed dates are not sent."),
        ("p", "To stop for good, click Stop. Invoices already sent are not affected."),
    ], applies="2.1.0+", plans=PLANS, related=["set-up-recurring-invoices"])
    art("recurring-invoices", "recurring-invoices-faq", "Recurring invoices: frequently asked questions", "2026-08-20", [
        ("h3", "Which time zone do schedules use?"), ("p", "Since 2.3.1, UTC internally. Dates are shown in your local time."),
        ("h3", "Can a recurring invoice charge a card automatically?"), ("p", "No. Clients pay from the invoice email or the portal."),
        ("h3", "Can I change the amount for one cycle?"), ("p", "Yes. Edit the generated draft before it is sent, or set the profile to create drafts."),
        ("h3", "What happens on the 31st in shorter months?"), ("p", "The invoice goes out on the last day of the month."),
    ], type="faq", applies="2.3.1+", plans=PLANS, related=["recurring-invoice-timezones", "recurring-cadences"])
    art("expenses", "expense-import-csv", "Import expenses from CSV", "2026-03-11", [
        ("p", "Go to Expenses > Import and upload a CSV with date, vendor, amount, currency, and category columns."),
        ("p", "Since 2.2.1, dates can be YYYY-MM-DD or DD/MM/YYYY. Before that, only YYYY-MM-DD worked (BUG-2110-02)."),
        ("p", "Up to 2,000 rows per file."),
    ], applies="2.1.0+", plans=PLANS, related=["expense-import-dates", "record-an-expense"])
    art("expenses", "mileage-expenses", "Mileage expenses", "2025-09-17", [
        ("p", "Record mileage as an expense: enter the distance and InvoicePilot multiplies it by your mileage rate."),
        ("p", "Set the rate under Settings > Expenses. Rates can be per mile or per kilometer."),
    ], applies="2.1.0+", plans=PLANS)
    art("estimates", "estimate-expiry", "Estimate expiry dates", "2025-06-20", [
        ("p", "Estimates can have an expiry date. After it passes, the client can no longer accept the estimate from the portal."),
        ("p", "You can extend an expired estimate by editing the expiry date and sending it again."),
    ], applies="2.0.0+", plans=PLANS, related=["create-estimate"])
    art("client-portal", "portal-payment-methods", "Payment methods in the client portal", "2026-01-22", [
        ("p", "Clients can pay by card or bank transfer (ACH in the US, SEPA in the EU)."),
        ("p", "Card payments are settled to your bank account in 2 business days. Bank transfers take 3 to 5 business days."),
        ("p", "Portal payments are created as payments automatically and trigger the payment.created webhook."),
    ], applies="2.2.0+", plans=PLANS, related=["client-portal-overview"])
    art("bank-reconciliation", "auto-match-rules", "How auto-match decides", "2026-06-01", [
        ("p", "Auto-match pairs a bank transaction with an invoice or expense when the amount matches exactly and the dates are within 7 days."),
        ("p", "If several invoices match, auto-match suggests them instead of matching, and you choose."),
        ("p", "On 2.3.1, foreign-currency amounts are not converted before they are compared (BUG-2310-01). Use manual matching for those transactions."),
    ], applies="2.3.0+", plans=PLANS, related=["auto-match", "review-suggested-matches"])
    art("bank-reconciliation", "disconnect-bank-feed", "Disconnect a bank feed", "2026-01-10", [
        ("p", "Go to Banking > Accounts, open the account, and click Disconnect feed. Imported transactions stay."),
        ("p", "Disconnecting frees a slot under your plan's limit: 2 feeds on Starter, 10 on Professional, unlimited on Enterprise."),
    ], applies="2.0.0+", plans=PLANS, related=["connect-bank-feed"])
    art("reports", "aged-receivables", "Aged receivables report", "2025-06-25", [
        ("p", "Shows what each client owes, grouped by how overdue it is: current, 1-30, 31-60, 61-90, and over 90 days."),
        ("p", "Click a client to see their invoices. Export as PDF or CSV, or XLSX on 2.3.0 and later."),
    ], applies="2.0.0+", plans=PLANS, related=["standard-reports"])
    art("reports", "tax-summary-report", "Tax summary report", "2025-08-03", [
        ("p", "Shows tax collected on invoices and tax paid on expenses for a date range, by tax rate."),
        ("p", "Archived tax rates still appear for the periods they were used."),
    ], applies="2.0.0+", plans=PLANS, related=["tax-rates"])
    art("account-billing", "change-plan", "Change your plan", "2026-03-02", [
        ("p", "Admins can upgrade at any time under Settings > Billing. The new limits apply right away."),
        ("p", "Downgrades take effect at the next renewal. Before you downgrade, make sure you are within the lower plan's limits, such as 2 bank feeds on Starter."),
        ("p", "Plan prices per seat per year: Starter $12, Professional $25, Enterprise $40."),
    ], applies="2.0.0+", plans=PLANS, related=["plans-and-limits", "renewals"])
    art("account-billing", "security-overview", "Security overview", "2026-04-15", [
        ("p", "InvoicePilot encrypts data in transit with TLS 1.2 or later and at rest with AES-256."),
        ("ul", ["Two-step verification for every user", "SOC 2 Type II report available on request",
                "Data hosted in the US and the EU", "Audit log on Enterprise (13 months)"]),
        ("p", "Single sign-on (SAML) is not available today."),
    ], type="guide", plans=PLANS, related=["sso-saml", "roles-and-audit-log"])
    art("support", "status-page", "Service status and incidents", "2026-06-02", [
        ("p", "Check status.invoicepilot.example for live status. Subscribe to get incident emails."),
        ("p", "If the API returns IP-5030 for many requests at once, a bank feed provider is usually down. Check the status page before you open a ticket."),
    ], type="guide", plans=PLANS, related=["contact-support"])
    art("support", "report-a-bug", "How to report a bug", "2026-03-01", [
        ("p", "Open a ticket with the steps to reproduce, the version shown under Help > About, and any error code such as IP-4220."),
        ("p", "If the bug is already tracked, support links your ticket to its BUG- ID and you get an email when it is fixed."),
    ], type="guide", plans=PLANS, related=["contact-support", "known-issues"])


# ---------------------------------------------------------------------------
# Help center: InvoicePilot Classic (1.x), still online, stale on purpose
# ---------------------------------------------------------------------------

def legacy_pages(art):
    L = "1.9.0"
    art("legacy", "classic-overview", "InvoicePilot Classic (1.x) documentation", "2025-01-20", [
        ("p", "These pages describe InvoicePilot Classic, versions 1.8.0 and 1.9.0. Classic was replaced by InvoicePilot 2.0.0 in June 2025."),
        ("note", "If you use InvoicePilot today, you are on 2.x. Use the main help center instead."),
    ], type="guide", applies="1.x")
    pages = [
        ("classic-late-fees", "Late fees (Classic)", "2025-01-20",
         [("p", "Classic can add a late fee to overdue invoices automatically: a fixed amount or a percentage of the subtotal."),
          ("p", "Turn it on under Settings > Late Fees. The fee is added 1 day after the due date."),
          ("p", "In 1.8.0 the fee was calculated on the total including tax (BUG-1800-02). Fixed in 1.9.0.")]),
        ("classic-currencies", "Currencies (Classic)", "2024-09-12",
         [("p", "Classic supports one currency per organization. To bill a client in another currency, convert the amounts yourself."),
          ("p", "Multi-currency invoicing is not available in Classic.")]),
        ("classic-recurring", "Repeating invoices (Classic)", "2024-09-12",
         [("p", "Classic has no automatic recurring invoices. Use Duplicate to copy last month's invoice."),
          ("p", "Some users set a calendar reminder to duplicate invoices each month.")]),
        ("classic-bank", "Bank statements (Classic)", "2024-09-12",
         [("p", "Classic has no live bank feeds. Import a bank statement CSV once a month and match each line by hand.")]),
        ("classic-api", "Classic API", "2025-01-20",
         [("p", "Classic integrations use API v1 at /v1 with page-based pagination: ?page=2&per_page=50."),
          ("p", "Errors are plain text messages with no error codes. Rate limit: 30 requests per minute on every plan.")]),
        ("classic-plans", "Classic plans", "2024-09-12",
         [("table", ["Plan", "Users", "Price per user per year"], [["Solo", "1", "$9"], ["Team", "Up to 10", "$18"], ["Business", "Unlimited", "$30"]]),
          ("p", "Classic plans were replaced by Starter, Professional, and Enterprise in 2.0.0.")]),
        ("classic-reports", "Reports (Classic)", "2025-03-05",
         [("p", "Classic has 8 standard reports. Custom reports are not available."),
          ("p", "Organizations with more than 5,000 invoices may see reports time out (BUG-1900-02). This was fixed in 2.0.0.")]),
        ("classic-estimates", "Estimates (Classic)", "2025-01-20",
         [("p", "Estimates were added in 1.9.0. Clients accept an estimate by replying to the email; there is no portal.")]),
        ("classic-attachments", "Attachments (Classic)", "2025-02-12",
         [("p", "In 1.9.0 you can attach files up to 10 MB."),
          ("p", "Emails with attachments over 5 MB can be delayed up to 2 hours (BUG-1900-01, Won't Fix).")]),
        ("classic-csv-export", "CSV export (Classic)", "2024-10-05",
         [("p", "Export invoices, payments, and expenses as CSV from each list."),
          ("p", "In 1.8.0 some locales got semicolon separators (BUG-1800-01). Fixed in 1.9.0.")]),
        ("classic-support", "Support for Classic", "2025-06-12",
         [("p", "Classic is no longer supported since 2.0.0 was released. All Classic organizations were moved to 2.0.0 automatically.")]),
        ("classic-migration", "Moving from Classic to 2.0.0", "2025-06-12",
         [("ol", ["Your data moves automatically: clients, invoices, payments, expenses, and estimates.",
                  "Late fee settings do not move, because 2.x has no automatic late fees.",
                  "Classic plans map to new plans: Solo and Team to Starter or Professional, Business to Enterprise.",
                  "API v1 keeps working after the move."])]),
    ]
    for slug, title, updated, body in pages:
        art("legacy", slug, title, updated, body, type="help_article", applies=L if slug != "classic-csv-export" else "1.8.0+")


# ---------------------------------------------------------------------------
# Community posts: low authority, some right, some wrong
# ---------------------------------------------------------------------------

COMMUNITY = [
    ("ip-4290-vs-4291", "IP-4290 vs IP-4291?", "api_amir", "2026-07-08",
     ["We started getting IP-4291 after moving our sync job to 20 workers. Turns out it's the concurrency limit (10 in flight), not the per-minute limit, which is IP-4290.",
      "Dropped to 8 workers and it's gone."]),
    ("webhook-signature-fails", "Webhook signature never matches", "nodedev_kim", "2026-06-22",
     ["Spent a day on this. You have to sign timestamp + '.' + the RAW body, not the parsed JSON re-serialized.",
      "Also use X-InvoicePilot-Timestamp, not your server time."]),
    ("starter-webhooks", "Webhooks on Starter?", "smallbiz_joe", "2026-06-30",
     ["Can't find the webhooks settings on Starter. Is it a bug?",
      "Reply: it's Professional and Enterprise only."]),
    ("duplicate-payments-api", "API created two payments", "erp_sam", "2026-04-09",
     ["Our retry logic created duplicate payments even with an Idempotency-Key. Support says BUG-2210-02 on 2.2.1.",
      "We now check GET /v2/payments before retrying."]),
    ("cursor-last-page", "Extra empty page at the end of every list call", "dev_priyanka", "2026-02-20",
     ["On 2.2.0 the last page still has a next_cursor and the next call returns nothing. Annoying but harmless.",
      "Reply: fixed in 2.2.1, next_cursor is null now."]),
    ("late-fees-gone", "Where did late fees go after the upgrade?", "classic_carol", "2025-06-20",
     ["We used automatic late fees in Classic and they're gone in 2.0.0.",
      "Reply: they weren't carried over. We add a line item now."]),
    ("auto-match-gbp", "Auto-match and GBP", "finops_dan", "2026-09-12",
     ["Following up on my EUR post. Same with GBP. We just leave foreign accounts on manual matching.",
      "Someone said the fix is coming in 2.4.0 but I haven't seen that anywhere official."]),
    ("bulk-void-50", "Bulk void limit", "ledger_lucy", "2026-03-02",
     ["Bulk void also caps at 50 for us. Do it in batches.",
      "Reply: mine lets me pick 100."]),
    ("pdf-25-lines", "Long invoices cut off in the PDF", "agency_ana", "2026-09-04",
     ["Our 40-line invoices only show the first page in the PDF. Known bug BUG-2310-02.",
      "We send the link instead. Clients see everything online."]),
    ("custom-roles-pro", "Custom roles on Professional?", "ops_rahul", "2026-05-18",
     ["Pretty sure we had custom roles on Professional. Can't find them now.",
      "Reply: custom roles are Enterprise only. You might be thinking of the 4 built-in roles."]),
    ("sandbox-reset", "Sandbox data disappeared", "qa_lin", "2026-03-01",
     ["All our sandbox test data was gone this morning.",
      "Reply: the sandbox resets on the first of every month."]),
    ("python-sdk-retries", "Does the Python SDK retry on its own?", "py_marco", "2026-08-15",
     ["Yes. client = Client(max_retries=3) and it retries 429, 500 and 503. It won't retry IP-4220 validation errors."]),
    ("statement-json", "Getting statements as JSON", "erp_sam", "2026-04-20",
     ["GET /v2/customers/{customer_id}/statements?format=json works. Saves us parsing PDFs."]),
    ("exchange-rate-weekend", "Weekend invoices used Friday's rate", "eu_freelancer", "2025-07-01",
     ["Noticed on 2.0.0 that invoices made on Sunday used Friday's EUR rate. Support says BUG-2000-03, fixed in 2.0.1."]),
    ("reminders-twice", "Clients got reminders twice", "studio_mei", "2025-10-20",
     ["Two identical reminders went out last night. Support linked it to BUG-2100-04. Our window was 23:00 to 01:00 UTC."]),
    ("receipt-sideways", "Receipt scanning reads nothing", "roadwarrior_tom", "2025-10-03",
     ["Landscape photos come out sideways and the amount is blank. Take them in portrait until the fix (BUG-2100-03)."]),
    ("expense-import-uk", "UK date format in expense import", "uk_books", "2025-12-08",
     ["Import fails with our DD/MM/YYYY dates. Converting to YYYY-MM-DD in Excel first works."]),
    ("partial-pay-portal", "Client can't pay the rest", "agency_ana", "2026-03-28",
     ["After a partial payment the portal hides Pay now. We send the payment link by hand. BUG-2210-01 apparently."]),
    ("api-v1-shutdown", "API v1 shutdown date?", "integrator_pat", "2026-08-01",
     ["Heard v1 shuts down at the end of 2026. Anyone confirm?",
      "Reply: docs still say no shutoff date and 12 months' notice. I'd ignore the rumor."]),
    ("sso-when", "SSO when?", "it_admin_ravi", "2026-07-14",
     ["We need SAML. Sales said 'soon'. Nothing on the roadmap page.",
      "Reply: same. No date anywhere."]),
    ("bank-feed-sync-time", "How often do feeds sync?", "newbie_ella", "2026-06-02",
     ["Is it once a day? The FAQ says that.", "Reply: every 4 hours since 2.3.0. The FAQ is old."]),
    ("ratelimit-headers", "No X-RateLimit headers?", "api_amir", "2026-02-05",
     ["On 2.2.0 there are no X-RateLimit-Remaining headers in v2 responses. Support says BUG-2200-02."]),
    ("idempotency-reuse", "IP-4090 on retry", "erp_sam", "2026-05-02",
     ["We got IP-4090 because our retry changed the body (new timestamp field) but kept the same Idempotency-Key. Keep the body identical."]),
    ("idempotency-processing", "IP-4091 what is it", "nodedev_kim", "2026-07-11",
     ["IP-4091 means the first request with that key is still running. Wait a second and retry, the SDK does it."]),
    ("multi-currency-starter", "Multi-currency on Starter?", "smallbiz_joe", "2025-08-10",
     ["Yes, multi-currency works on Starter. Settings > Currencies."]),
    ("estimate-convert-422", "Can't convert estimate via API", "erp_sam", "2026-04-15",
     ["POST /v2/estimates/{estimate_id}/convert gives IP-4225. The estimate has to be accepted first."]),
    ("archived-customer-422", "IP-4223 creating invoice", "integrator_pat", "2026-07-15",
     ["IP-4223 means the customer is archived. Unarchive it first."]),
    ("currency-not-enabled", "IP-4222 on EUR invoice", "eu_freelancer", "2026-07-18",
     ["Got IP-4222 creating an EUR invoice. Had to enable EUR under Settings > Currencies."]),
    ("webhook-disabled", "Webhook endpoint disabled itself", "nodedev_kim", "2026-08-05",
     ["Our endpoint was down for a long weekend and InvoicePilot disabled it. It's after 3 days of failures. Re-enable in settings."]),
    ("webhook-retries-5", "How many webhook retries?", "py_marco", "2026-07-02",
     ["Webhooks retry 5 times then give up.", "Reply: I think they changed it recently."]),
    ("audit-log-length", "Audit log history", "it_admin_ravi", "2026-04-02",
     ["Enterprise audit log keeps 13 months. We export it monthly for longer retention."]),
    ("seats-proration", "Are added seats prorated?", "ops_rahul", "2026-02-12",
     ["No, added seats are full price for their own 12-month term. Plan ahead."]),
    ("report-3-years", "Report builder times out", "cfo_greta", "2026-06-10",
     ["5-year revenue report times out. BUG-2300-01. Split into 3-year chunks and combine in Excel."]),
    ("week-start-sunday", "Date picker starts on Sunday", "eu_freelancer", "2026-09-06",
     ["Report date picker ignores our Monday locale. BUG-2310-03, cosmetic only."]),
    ("classic-api-rate", "Classic API rate limit", "classic_carol", "2025-02-01",
     ["Classic API is 30 requests a minute for everyone. Painful for our sync."]),
    ("credit-note-vs-void", "Credit note or void?", "studio_mei", "2026-02-20",
     ["Void if the invoice was a mistake. Credit note if the client is owed something back. Credit notes show on statements."]),
    ("mileage-km", "Mileage in kilometers", "eu_freelancer", "2025-09-25",
     ["You can set the mileage rate per km in Settings > Expenses."]),
    ("portal-ach", "ACH in the portal", "smallbiz_joe", "2026-02-01",
     ["Clients can pay by ACH from the portal now. Takes 3-5 business days to land."]),
    ("tax-rate-change-old", "Changing tax rate changed old invoices?", "newbie_ella", "2025-08-15",
     ["I was worried, but no, old invoices keep their rate. Only new ones use the new rate."]),
    ("dashboard-blank", "Blank dashboard", "big_ledger", "2025-06-29",
     ["Dashboard is blank for us, we have ~800 contacts. Support says BUG-2000-02 and a fix is rolling out."]),
]


# ---------------------------------------------------------------------------
# Support tickets (JSON). Each scenario is grounded in a fact from the docs.
# ---------------------------------------------------------------------------

AGENTS = ["Maya (Support)", "Leo (Support)", "Priya (Support)", "Sam (Support)", "Nora (Support Tier 2)"]

SCENARIOS = [
    # key, versions allowed, subject variants, customer message variants, agent reply, tags, linked bug, wrong reply?
    dict(k="ip4220", v=["2.2.0", "2.2.1", "2.3.0", "2.3.1"],
         subj=["API error IP-4220 when creating invoices", "Getting IP-4220 from POST /v2/invoices", "422 IP-4220 validation error"],
         msg=["Our integration gets IP-4220 on some invoices. Message says line_items[2].quantity must be greater than 0. Should we retry?",
              "We see HTTP 422 with code IP-4220 when we push invoices from our ERP. Is your API down?"],
         reply="IP-4220 means validation failed, and the message tells you which field. It is not retryable: fix the data (here, a quantity of 0) and send it again. "
               "If you want more detail, newer responses may include a subcode like IP-4221 for line item problems.",
         tags=["api", "errors"]),
    dict(k="ip4290", v=["2.2.0", "2.2.1", "2.3.0", "2.3.1"],
         subj=["IP-4290 rate limit errors", "Too many requests from our sync", "429 IP-4290 during nightly import"],
         msg=["Our nightly import fails with 429 and IP-4290. We're on {plan}. What's our limit?",
              "We keep hitting IP-4290. Can you raise our rate limit?"],
         reply="IP-4290 means the per-minute rate limit was reached. Your plan allows {rpm} requests per minute. Wait for the number of seconds in the Retry-After header, then retry. "
               "If you run many requests in parallel, also watch for IP-4291, which is the separate limit of 10 requests in flight.",
         tags=["api", "rate-limit"]),
    dict(k="ip4291", v=["2.2.1", "2.3.0", "2.3.1"],
         subj=["IP-4291 errors after scaling workers", "What is IP-4291?"],
         msg=["We moved our sync to 16 parallel workers and now get IP-4291. We're well under our per-minute limit.",
              "Getting 429 with IP-4291, not IP-4290. What's the difference?"],
         reply="IP-4291 is the concurrency limit: at most 10 requests in flight per API key, on every plan. IP-4290 is the per-minute limit. Keep 10 or fewer requests in parallel and retry after Retry-After.",
         tags=["api", "rate-limit"]),
    dict(k="ip4090", v=["2.2.0", "2.2.1", "2.3.0", "2.3.1"],
         subj=["IP-4090 conflict on retry", "Idempotency error IP-4090"],
         msg=["Our retries fail with 409 IP-4090. We reuse the Idempotency-Key from the first attempt.",
              "Getting IP-4090 when our job retries after a timeout."],
         reply="IP-4090 means the Idempotency-Key was reused with a different request body. Retries must send exactly the same body with the same key. This error is not retryable as-is. "
               "If the first request is still running you would get IP-4091 instead, which you can retry after a second.",
         tags=["api", "idempotency"]),
    dict(k="ip5030", v=["2.2.0", "2.2.1", "2.3.0", "2.3.1"],
         subj=["Lots of IP-5030 errors this morning", "503 IP-5030 from bank endpoints"],
         msg=["Since 8am our bank sync gets 503 with IP-5030 on almost every call.",
              "Is something down? IP-5030 everywhere."],
         reply="IP-5030 means a bank feed provider is unavailable. It is retryable with backoff. We had a provider incident this morning; see status.invoicepilot.example. Your requests should succeed once it recovers.",
         tags=["api", "bank-feeds", "incident"]),
    dict(k="ip4010", v=["2.2.0", "2.2.1", "2.3.0", "2.3.1"],
         subj=["401 IP-4010 with a new key", "API says IP-4010"],
         msg=["We created a key yesterday and every call returns IP-4010.", "Getting IP-4010 in production but the sandbox works."],
         reply="IP-4010 means the API key is missing or invalid. Check the Authorization: Bearer header. Production needs an ip_live_ key; ip_test_ keys only work in the sandbox.",
         tags=["api", "auth"]),
    dict(k="ip4030", v=["2.2.0", "2.2.1", "2.3.0", "2.3.1"],
         subj=["403 IP-4030 on POST", "IP-4030 permission error"],
         msg=["Our key can read invoices but POST /v2/invoices returns IP-4030.", "IP-4030 when connecting a third bank account by API."],
         reply="IP-4030 means the key lacks permission or you hit a plan limit. A read-only key cannot create invoices. On Starter you can connect 2 bank feeds. It is not retryable.",
         tags=["api", "permissions"]),
    dict(k="bug231001", v=["2.3.1"], bug="BUG-2310-01",
         subj=["Auto-match not matching our EUR transactions", "Multi-currency auto-match broken", "GBP feed: nothing auto-matches"],
         msg=["Since the 2.3.1 update, our {cur} bank account barely auto-matches anything. Base currency works fine.",
              "Auto-match suggests wrong amounts for our {cur} account."],
         reply="This is BUG-2310-01 (Critical, open): on 2.3.1, auto-match does not convert foreign-currency amounts before comparing them. Please match foreign-currency transactions manually for now, and don't bulk-confirm suggested matches on that account. "
               "I can't share a fix date, but your ticket is linked and you'll get an email when it ships.",
         tags=["bank-reconciliation", "multi-currency", "bug"]),
    dict(k="bug231002", v=["2.3.1"], bug="BUG-2310-02",
         subj=["Invoice PDF missing line items", "PDF only shows the first page", "Long invoice cut off"],
         msg=["Our invoice has {n} lines but the PDF stops after the first page.", "Client says the PDF we sent is missing items."],
         reply="This is BUG-2310-02 (High, open): invoices with more than 25 line items export as a single-page PDF. Send the invoice by email link instead; the online view and the portal show every line. Or keep invoices to 25 lines or fewer.",
         tags=["invoicing", "pdf", "bug"]),
    dict(k="bug231003", v=["2.3.1"], bug="BUG-2310-03",
         subj=["Report date picker starts on Sunday", "Week start wrong in report builder"],
         msg=["Our locale is set to Monday but the report date picker starts weeks on Sunday. Are our weekly numbers wrong?"],
         reply="That's BUG-2310-03 (Low, open). It is cosmetic: the picker always starts on Sunday, but the report data is correct.",
         tags=["reports", "bug"]),
    dict(k="bug230001", v=["2.3.0", "2.3.1"], bug="BUG-2300-01",
         subj=["Custom report times out", "5-year report never finishes"],
         msg=["Our 5-year revenue report in the custom report builder times out.", "Report spanning 2021-2026 just spins and fails."],
         reply="That's BUG-2300-01 (Medium, open): reports spanning more than 3 years time out. Split the report into ranges of 3 years or less, or use API v2, which pages with a cursor.",
         tags=["reports", "bug"]),
    dict(k="bug210002", v=["2.1.0", "2.1.1", "2.2.0", "2.2.1", "2.3.0"], bug="BUG-2100-02",
         subj=["Recurring invoice didn't go out", "Missed a monthly invoice in March", "Recurring invoice skipped a cycle"],
         msg=["One of our monthly recurring invoices just didn't send this cycle. Others did.", "A client says they never got their November invoice from the recurring profile."],
         reply="This looks like BUG-2100-02: recurring schedules calculated in local time can skip a cycle when daylight-saving time changes. It is fixed in 2.3.1, which moves schedules to UTC. For now, send the missed invoice by hand from the profile.",
         tags=["recurring-invoices", "bug"]),
    dict(k="bug220001", v=["2.2.0"], bug="BUG-2200-01",
         subj=["Client stuck in login loop", "Portal keeps sending client back to sign in"],
         msg=["A client on a Mac says the portal sends them back to the login page right after they sign in."],
         reply="That's BUG-2200-01, a Safari login loop caused by a cookie SameSite setting. A fix is already rolling out in 2.2.0. Ask the client to clear cookies for the portal and sign in again.",
         tags=["client-portal", "bug"]),
    dict(k="bug220002", v=["2.2.0", "2.2.1"], bug="BUG-2200-02",
         subj=["No rate limit headers in v2", "X-RateLimit-Remaining missing"],
         msg=["We want to back off before hitting limits but v2 responses have no X-RateLimit-* headers."],
         reply="That's BUG-2200-02 (Low): API v2 responses are missing the X-RateLimit-* headers. It's fixed in 2.3.0. Until then, rely on the 429 response and Retry-After.",
         tags=["api", "bug"]),
    dict(k="bug220003", v=["2.2.0"], bug="BUG-2200-03",
         subj=["Clients got reminders for voided invoices", "Reminders after bulk void"],
         msg=["We voided 60 invoices in bulk and clients still got payment reminders for them."],
         reply="That's BUG-2200-03: a bulk void leaves scheduled reminders in place. It will be fixed in 2.2.1. For now, cancel the reminders from each client's Reminders tab.",
         tags=["invoicing", "reminders", "bug"]),
    dict(k="bug220004", v=["2.2.0"], bug="BUG-2200-04",
         subj=["Extra empty page from list endpoints", "next_cursor not null on last page"],
         msg=["GET /v2/invoices returns a next_cursor on the last page, and the next call is empty."],
         reply="That's BUG-2200-04 (Medium). It's harmless but wasteful. It's fixed in 2.2.1, where next_cursor is null on the last page. Until then, stop when data comes back empty.",
         tags=["api", "pagination", "bug"]),
    dict(k="bug221001", v=["2.2.1"], bug="BUG-2210-01",
         subj=["Client can't pay remaining balance", "Pay now missing after partial payment"],
         msg=["A client paid half an invoice in the portal and now there's no Pay now button for the rest."],
         reply="That's BUG-2210-01 (High): the Pay now button is hidden for partially paid invoices on 2.2.1. It's fixed in 2.3.0. Meanwhile, open the invoice and use More > Copy payment link, then send that to the client.",
         tags=["client-portal", "payments", "bug"]),
    dict(k="bug221002", v=["2.2.1"], bug="BUG-2210-02",
         subj=["Duplicate payments from our integration", "Idempotency-Key not working on payments"],
         msg=["Our ERP retried POST /v2/payments after a timeout with the same Idempotency-Key and we got two payments."],
         reply="That's BUG-2210-02 (High): on 2.2.1 the Idempotency-Key is ignored on POST /v2/payments only. It's fixed in 2.3.0. Delete the duplicate with DELETE /v2/payments/{payment_id}, which reopens the invoice, and check GET /v2/payments before retrying.",
         tags=["api", "payments", "bug"]),
    dict(k="bug200003", v=["2.0.0"], bug="BUG-2000-03",
         subj=["Weekend invoice used old exchange rate"], msg=["An EUR invoice we made on Sunday used Friday's rate."],
         reply="That's BUG-2000-03: rates aren't refreshed on weekends on 2.0.0. It's fixed in 2.0.1. You can edit the rate on the invoice.",
         tags=["multi-currency", "bug"]),
    dict(k="bug200004", v=["2.0.0"], bug="BUG-2000-04",
         subj=["Gap in invoice numbers"], msg=["We deleted a draft and now INV-000213 is missing from the sequence. Our auditor asked about it."],
         reply="That's BUG-2000-04: on 2.0.0, deleting a draft uses up its number. It's fixed in 2.0.1. The gap stays, but the Invoice Register report shows the deleted draft for your auditor.",
         tags=["invoicing", "bug"]),
    dict(k="bug210004", v=["2.1.0"], bug="BUG-2100-04",
         subj=["Reminder sent twice"], msg=["Two clients got the same payment reminder twice last night."],
         reply="That's BUG-2100-04: reminders with a send window crossing midnight UTC go out twice on 2.1.0. Fixed in 2.1.1. Until then, set the window so it doesn't cross midnight UTC.",
         tags=["reminders", "bug"]),
    dict(k="bug210003", v=["2.1.0"], bug="BUG-2100-03",
         subj=["Receipt scan misses the amount"], msg=["Receipts photographed sideways come out rotated and the total is blank."],
         reply="That's BUG-2100-03, fixed in 2.1.1. Take the photo in portrait for now, or type the amount.",
         tags=["expenses", "bug"]),
    dict(k="bug210001", v=["2.1.0", "2.1.1", "2.2.0", "2.3.1"], bug="BUG-2100-01",
         subj=["Handwritten receipts not scanned"], msg=["Receipt scanning doesn't read our handwritten taxi receipts at all."],
         reply="Handwritten receipts are a known limitation, BUG-2100-01 (Low, Won't Fix): OCR accuracy on handwriting is below 40%. Typed and printed receipts scan reliably. Please type the amount for handwritten ones.",
         tags=["expenses"]),
    dict(k="bug211002", v=["2.1.1", "2.2.0"], bug="BUG-2110-02",
         subj=["Expense import fails on dates"], msg=["Our CSV has dates like 31/01/2026 and the import rejects every row."],
         reply="That's BUG-2110-02: DD/MM/YYYY dates are rejected. It will be fixed in 2.2.1. For now, convert the dates to YYYY-MM-DD.",
         tags=["expenses", "import", "bug"]),
    dict(k="webhooks_starter", v=["2.3.0", "2.3.1"],
         subj=["Can't find webhooks", "Webhooks on our plan?"],
         msg=["We're on {plan} and can't find webhook settings.", "Do we have webhooks on {plan}?"],
         reply="Webhooks are available on Professional (5 endpoints) and Enterprise (25 endpoints). {planline}",
         tags=["api", "webhooks", "plans"]),
    dict(k="webhook_sig", v=["2.3.0", "2.3.1"],
         subj=["Webhook signature mismatch", "X-InvoicePilot-Signature never matches"],
         msg=["Our HMAC check on X-InvoicePilot-Signature always fails."],
         reply="Sign the X-InvoicePilot-Timestamp value, a dot, and the raw request body, using your whsec_ secret with HMAC-SHA256. Don't re-serialize the JSON. Also reject timestamps older than 5 minutes. The Python SDK has client.webhooks.verify_signature for this.",
         tags=["api", "webhooks"]),
    dict(k="webhook_disabled", v=["2.3.0", "2.3.1"],
         subj=["Webhook endpoint disabled", "Stopped receiving webhooks"],
         msg=["We stopped getting webhooks after our server was down over the weekend."],
         reply="Endpoints are disabled after 3 days of failed deliveries. Re-enable it under Settings > Developer > Webhooks. Each failed delivery is retried up to 8 times over 24 hours, so events from before that window are not resent; use the API to catch up.",
         tags=["api", "webhooks"]),
    dict(k="custom_roles", v=["2.2.0", "2.3.0", "2.3.1"],
         subj=["Custom roles", "Can we create our own user roles?"],
         msg=["We're on {plan}. Can we make a role that can create invoices but not see reports?"],
         reply="Custom roles are Enterprise only. Other plans use the four built-in roles: Admin, Accountant, Staff, and Read-only.",
         wrong="Yes, custom roles are available on Professional and Enterprise. Go to Settings > Roles.",
         tags=["account", "roles", "plans"]),
    dict(k="bulk_limit", v=["2.2.0", "2.2.1", "2.3.0", "2.3.1"],
         subj=["How many invoices in a bulk action?", "Bulk send limit"],
         msg=["How many invoices can we send at once from the list? We have about 300 at month end."],
         reply="You can select up to 100 invoices per bulk action. For 300, filter the list and repeat three times.",
         wrong="Bulk actions are limited to 50 invoices at a time, so do it in batches of 50.",
         tags=["invoicing", "bulk"]),
    dict(k="bank_feeds_limit", v=["2.0.0", "2.2.0", "2.3.0", "2.3.1"],
         subj=["How many bank accounts can we connect?"],
         msg=["We're on {plan}. How many bank feeds can we connect?"],
         reply="Starter includes 2 connected bank feeds, Professional 10, and Enterprise unlimited. You're on {plan}, so your limit is {feeds}.",
         tags=["bank-feeds", "plans"]),
    dict(k="feed_sync", v=["2.3.0", "2.3.1"],
         subj=["How often do bank feeds update?"],
         msg=["The FAQ says feeds sync once a day but we see new transactions more often. Which is right?"],
         reply="Since 2.3.0, bank feeds sync every 4 hours. The FAQ page is out of date; we've flagged it.",
         tags=["bank-feeds"]),
    dict(k="sso", v=["2.1.0", "2.2.0", "2.3.0", "2.3.1"],
         subj=["SSO / SAML support", "Do you support Okta SSO?"],
         msg=["Our IT team requires SAML SSO. When will you support it?"],
         reply="Single sign-on (SAML) isn't available today, and I don't have a date to share. Every user can turn on two-step verification in the meantime.",
         tags=["security", "sso"]),
    dict(k="api_v1", v=["2.2.0", "2.2.1", "2.3.0", "2.3.1"],
         subj=["Is API v1 being shut down?", "Do we need to migrate to v2?"],
         msg=["We still use API v1. Will it stop working?"],
         reply="API v1 is legacy but still works, and there is no shutoff date yet. We'll give at least 12 months' notice. New integrations should use v2, which adds cursor pagination, error codes, and Idempotency-Key.",
         tags=["api", "v1"]),
    dict(k="statements_json", v=["2.2.0", "2.3.0", "2.3.1"],
         subj=["Statements via API"], msg=["Can we pull customer statements as JSON for our ERP?"],
         reply="Yes: GET /v2/customers/{customer_id}/statements with format=json, plus date_from and date_to. In the Python SDK it's client.customers.get_statement(customer_id, format=\"json\").",
         tags=["api", "statements"]),
    dict(k="late_fees", v=["2.0.0", "2.1.0", "2.2.0", "2.3.1"],
         subj=["Late fees setting missing", "Automatic late fees?"],
         msg=["We used automatic late fees in Classic. Where's the setting now?"],
         reply="Automatic late fees were part of InvoicePilot Classic (1.x) and weren't carried over to 2.x. You can add a late fee as a line item or a separate invoice, and mention your terms in payment reminders.",
         tags=["invoicing", "classic"]),
    dict(k="seat_proration", v=["2.1.0", "2.2.0", "2.3.0", "2.3.1"],
         subj=["Adding seats mid-year"], msg=["If we add 10 seats now, are they prorated to our renewal date?"],
         reply="Added seats aren't prorated. They're billed at the full per-seat price and start their own 12-month term.",
         wrong="Yes, added seats are prorated to your next renewal date.",
         tags=["billing", "seats"]),
    dict(k="xlsx_export", v=["2.2.0", "2.2.1", "2.3.0"],
         subj=["Export reports to Excel"], msg=["Can we export reports to Excel? We're on {ver}."],
         reply="XLSX export arrived in 2.3.0. {xlsx}",
         tags=["reports"]),
    dict(k="auto_match_ver", v=["2.2.0", "2.2.1"],
         subj=["Automatic bank matching?"], msg=["Does InvoicePilot match bank transactions automatically? We're on {ver}."],
         reply="Auto-match was added in 2.3.0. On {ver}, reconcile manually: match each transaction to an invoice or expense, or categorize it. You'll get auto-match automatically when you move to 2.3.x.",
         tags=["bank-reconciliation"]),
    dict(k="sandbox_reset", v=["2.2.0", "2.3.0", "2.3.1"],
         subj=["Sandbox data gone"], msg=["All our test invoices disappeared from the sandbox."],
         reply="The sandbox resets on the first day of every month. Re-create test data with a setup script after each reset.",
         tags=["api", "sandbox"]),
    dict(k="sdk_retry", v=["2.3.0", "2.3.1"],
         subj=["Python SDK retries", "Does the SDK retry 429s?"],
         msg=["Do we need our own retry logic with the Python SDK?"],
         reply="The Python SDK retries IP-4290, IP-4291, IP-5000, and IP-5030 automatically with backoff, up to max_retries (default 2). It never retries 4xx validation errors like IP-4220. Pass idempotency_key on creates so retries are safe.",
         tags=["api", "sdk"]),
]


def pick_date(versions):
    """A date when one of `versions` was the current release."""
    rel = dict(ALL_RELEASES)
    order = [v for v, _ in ALL_RELEASES]
    v = random.choice(versions)
    start = date.fromisoformat(rel[v])
    i = order.index(v)
    end = date.fromisoformat(rel[order[i + 1]]) - timedelta(days=1) if i + 1 < len(order) else TODAY
    d = start + timedelta(days=random.randint(0, max(0, (end - start).days)))
    return v, d


def make_tickets(customers, wrong_log, B):
    bug_fixed = {k: b["fixed_in_version"] for k, b in B.items()}
    rpm ={"Starter": "60", "Professional": "300", "Enterprise": "1,000"}
    feeds = {"Starter": "2", "Professional": "10", "Enterprise": "unlimited"}
    tickets, n = [], 20001
    for sc in SCENARIOS:
        count = 5 if len(sc["v"]) > 1 else 4
        for j in range(count):
            ver, d = pick_date(sc["v"])
            cust = random.choice([c for c in customers if c["signup_date"] <= d.isoformat()] or customers)
            plan = cust["account_tier"]
            if sc.get("bug"):
                status = "Linked to bug" if not bug_fixed.get(sc["bug"]) else "Solved"
            else:
                status = random.choice(["Solved", "Solved", "Solved", "Open", "Pending"])
            fill = dict(plan=plan, rpm=rpm[plan], feeds=feeds[plan], cur=random.choice(["EUR", "GBP", "CAD", "JPY"]),
                        n=random.choice([30, 42, 57, 64]), ver=ver,
                        planline="You're on Starter, so you'd need to upgrade to use them." if plan == "Starter"
                        else f"You're on {plan}, so look under Settings > Developer > Webhooks.",
                        xlsx="On your version, export to PDF or CSV and open the CSV in Excel." if ver < "2.3.0"
                        else "Pick XLSX in the export menu.")
            reply = sc["reply"]
            wrong = sc.get("wrong") and j == 0  # one wrong agent answer per scenario that has one
            if wrong:
                reply = sc["wrong"]
            tid = f"TCKT-{n}"
            n += 1
            h0 = random.randint(8, 15)
            t0 = datetime_str(d, h0)
            gap = random.choice([1, 2, 3, 5, 20, 26])  # hours until the agent replies
            t1 = datetime_str(d + timedelta(days=(h0 + gap) // 24), (h0 + gap) % 24)
            msgs = [{"from": "customer", "name": f"{cust['company_name']} admin", "sent_at": t0,
                     "body": fmt(random.choice(sc["msg"]), fill)},
                    {"from": "agent", "name": random.choice(AGENTS), "sent_at": t1, "body": fmt(reply, fill)}]
            if random.random() < 0.35:
                msgs.append({"from": "customer", "name": f"{cust['company_name']} admin",
                             "sent_at": datetime_str(d + timedelta(days=(h0 + gap + 18) // 24), (h0 + gap + 18) % 24),
                             "body": random.choice(["Thanks, that worked.", "Got it, thanks.", "OK. Please let us know when it's fixed.",
                                                    "That's not great, but we'll use the workaround."])})
            ticket = {
                "ticket_id": tid, "created_at": t0, "customer_id": cust["customer_id"], "company": cust["company_name"],
                "plan": plan, "product_version": ver, "subject": fmt(random.choice(sc["subj"]), fill),
                "status": status,
                "tags": sc["tags"], "linked_bug_id": sc.get("bug"), "messages": msgs,
            }
            tickets.append(ticket)
            if wrong:
                wrong_log.append((tid, sc["k"], reply))
    return tickets


def fmt(s, fill):
    """Fill {plan}-style slots but leave API paths like {payment_id} alone."""
    return re.sub(r"\{(\w+)\}", lambda m: str(fill.get(m.group(1), m.group(0))), s)


def datetime_str(d, hour):
    return f"{d.isoformat()}T{hour:02d}:{random.randint(0, 59):02d}:00Z"


# ---------------------------------------------------------------------------
# Engineering notes (Markdown + YAML front matter). Internal audience.
# ---------------------------------------------------------------------------

def eng_docs(B):
    docs = []

    def md(name, title, kind, updated, body, related_bugs=(), owner="platform-team", status="final"):
        fm = ["---", f"title: {title}", f"doc_type: {kind}", "audience: internal", f"owner: {owner}",
              f"status: {status}", f"last_updated: {updated}"]
        if related_bugs:
            fm.append("related_bugs: [" + ", ".join(related_bugs) + "]")
        fm.append("---")
        docs.append((name, "\n".join(fm) + "\n\n# " + title + "\n\n" + body.strip() + "\n"))

    # Postmortems for bugs that hurt customers
    pm = [
        ("BUG-2100-02", "INC-2025-031", "2025-11-02", "Recurring invoices skipped across the DST change",
         "Schedules were stored as local wall-clock times. On 2025-11-02 clocks went back one hour in the US, and the scheduler's "
         "'next run' calculation landed in a time that it had already passed, so 312 profiles skipped one cycle.",
         "Short term: support re-sent missed invoices by hand. Long term: ADR-014 moves schedule math to UTC. Shipped in 2.3.1.",
         "312 recurring profiles across 41 organizations missed one invoice."),
        ("BUG-2200-01", "INC-2026-004", "2026-01-25", "Safari client portal login loop",
         "The new portal session cookie was set with SameSite=Strict. Safari dropped it on the redirect from the sign-in page, so users were sent back to sign in.",
         "Changed the cookie to SameSite=Lax and redeployed within 2.2.0 on 2026-01-27.", "About 9% of portal sign-ins failed for 2 days."),
        ("BUG-2210-02", "INC-2026-011", "2026-04-06", "Duplicate payments from API retries",
         "A refactor of the payments service in 2.2.1 moved the payment write before the idempotency check. Retries with the same Idempotency-Key created a second payment.",
         "Restored the check order and added a test for every POST endpoint. Fixed in 2.3.0. A script found and listed 214 duplicate payments for support.",
         "214 duplicate payments across 9 API customers."),
        ("BUG-2310-01", "INC-2026-019", "2026-08-25", "Auto-match fails on multi-currency accounts",
         "In 2.3.1 the matching service was moved to a new amount comparator that skips the currency conversion step. Foreign-currency transactions are compared in their own currency against base-currency invoices.",
         "Workaround published: manual matching for foreign-currency transactions. The fix needs the comparator to load daily rates; see the planning note.",
         "Every organization with a foreign-currency bank account on 2.3.1. Critical severity."),
        ("BUG-2310-02", "INC-2026-021", "2026-08-29", "PDF export drops pages after 25 line items",
         "The new PDF renderer in 2.3.1 sets a fixed page height for the line item table. Rows past the first page are clipped instead of flowing to page 2.",
         "Workaround: send by link. A fix to the renderer's pagination is in progress.", "Invoices with more than 25 line items; about 3% of invoices sent."),
        ("BUG-2000-02", "INC-2025-012", "2025-06-28", "Blank dashboard for large accounts",
         "The dashboard loaded every contact in one query. For accounts with more than 500 contacts the query timed out after 30 seconds.",
         "Paginated the contacts query. Fixed within 2.0.0 on 2025-07-01.", "About 60 large organizations."),
        ("BUG-2000-01", "INC-2025-010", "2025-06-22", "JPY invoice totals rounded wrong",
         "Line totals were rounded to 2 decimals before summing, which is wrong for zero-decimal currencies like JPY and KRW.",
         "Round per currency's minor units. Fixed in 2.1.0. Finance issued credits to affected customers.", "Up to 1 yen per line item overcharged."),
        ("BUG-2200-03", "INC-2026-007", "2026-02-09", "Reminders sent for voided invoices",
         "The bulk void path did not call the reminder scheduler's cancel method, unlike the single-invoice void.",
         "Bulk void now cancels reminders. Fixed in 2.2.1.", "About 1,900 reminder emails for void invoices."),
    ]
    for bug_id, inc, d, title, cause, fix, impact in pm:
        b = B[bug_id]
        md(f"postmortem-{inc.lower()}", f"Postmortem {inc}: {title}", "postmortem", d, f"""
**Incident:** {inc}
**Bug:** {bug_id} ({b['severity']})
**Affected version:** {b['affected_version']}
**Fixed in:** {b['fixed_in_version'] or 'not yet fixed'}

## Impact
{impact}

## Root cause
{cause}

## Resolution
{fix}

## Customer communication
Support linked affected tickets to {bug_id}. Customers get an email when the fix ships.
""", related_bugs=[bug_id])

    # One outage that explains IP-5030 spikes
    md("postmortem-inc-2026-016", "Postmortem INC-2026-016: Bank feed provider outage", "postmortem", "2026-06-02", """
**Incident:** INC-2026-016
**Date:** 2026-06-01, 08:05 to 11:40 UTC

## Impact
Bank feed sync failed for US accounts using our main aggregator. API calls to bank endpoints returned HTTP 503 with IP-5030.

## Root cause
The aggregator had an outage. Our sync retried too fast and was throttled after they recovered.

## Resolution
Added jittered backoff to sync retries. IP-5030 is the correct code for this case and clients should retry with backoff.
""")

    # Design notes (ADRs)
    adrs = [
        ("adr-014-utc-schedules", "ADR-014: Calculate recurring schedules in UTC", "2026-06-20",
         "## Decision\nStore and calculate recurring schedules in UTC. Show them in the organization's local time.\n\n"
         "## Why\nLocal wall-clock math broke twice a year at DST changes (BUG-2100-02).\n\n"
         "## Consequences\nShipped in 2.3.1. The old help page about local-time schedules is stale and should be retired."),
        ("adr-009-cursor-pagination", "ADR-009: Cursor pagination for API v2", "2025-11-10",
         "## Decision\nv2 list endpoints use opaque cursors (next_cursor) with limit up to 100, instead of v1's ?page=&per_page=.\n\n"
         "## Why\nPage numbers skip or repeat rows when data changes between calls.\n\n"
         "## Note\n2.2.0 returned a cursor on the last page by mistake (BUG-2200-04); fixed in 2.2.1."),
        ("adr-010-idempotency", "ADR-010: Idempotency keys for POST", "2025-11-18",
         "## Decision\nPOST endpoints accept an Idempotency-Key header. We store the key with a hash of the body for 24 hours.\n\n"
         "## Behavior\nSame key and same body returns the stored response. Same key and a different body returns 409 IP-4090. "
         "A key whose first request is still running returns 409 IP-4091."),
        ("adr-017-concurrency-limit", "ADR-017: Per-key concurrency limit", "2026-06-25",
         "## Decision\nLimit each API key to 10 requests in flight, on every plan. Over the limit returns 429 IP-4291.\n\n"
         "## Why\nA few integrations ran 50+ parallel workers and caused slowdowns for everyone, while staying under their per-minute limit."),
        ("adr-018-webhook-retries", "ADR-018: Webhook retry schedule", "2026-07-15",
         "## Decision\nRetry failed webhook deliveries up to 8 times over 24 hours (was 5). Disable an endpoint after 3 days of failures.\n\n"
         "## Why\n5 retries over 6 hours missed weekend outages at small customers."),
        ("adr-012-pdf-renderer", "ADR-012: New PDF renderer", "2026-07-01",
         "## Decision\nReplace the HTML-to-PDF service with a native renderer in 2.3.1 for speed.\n\n"
         "## Risk noted\nTable pagination needs more testing. (Later: BUG-2310-02.)"),
    ]
    for name, title, d, body in adrs:
        md(name, title, "design_note", d, body)

    md("planning-q4-2026-fixes", "Planning note: Q4 2026 fix targets", "planning", "2026-10-01", """
Tentative targets for the next minor release (2.4.0). Nothing here is committed.

| Bug | Target | Confidence |
| --- | --- | --- |
| BUG-2310-01 | 2.4.0 | Medium |
| BUG-2310-02 | 2.4.0 | High |
| BUG-2310-03 | Later | Low |
| BUG-2300-01 | 2.4.0 | Medium |

**Do not share dates with customers.** Support and sales should say there is no committed fix date.
""", owner="product", status="draft")

    # Runbooks
    runbooks = [
        ("runbook-critical-bug-escalation", "Runbook: escalating a Critical bug", "2026-03-15",
         "1. Support tags the ticket critical and links the BUG- ID.\n2. On-call engineer is paged within 15 minutes.\n"
         "3. Enterprise customers get an update every 4 hours until resolved; this matches the 24/7 handling promised for Critical issues.\n"
         "4. Post a status page incident if more than 50 organizations are affected."),
        ("runbook-ip5030-spike", "Runbook: IP-5030 spike", "2026-06-03",
         "1. Check the aggregator status dashboard.\n2. If the provider is down, post a status page incident.\n"
         "3. Do not ask customers to change anything. IP-5030 is retryable with backoff."),
        ("runbook-duplicate-payments", "Runbook: cleaning up duplicate API payments", "2026-04-10",
         "1. Run the duplicate-payments report for the organization.\n2. Confirm with the customer which payment to keep.\n"
         "3. Delete the duplicate with DELETE /v2/payments/{payment_id}. The invoice reopens and then closes again when the right payment is applied."),
        ("runbook-webhook-disabled", "Runbook: customer endpoint disabled", "2026-08-01",
         "1. Check the endpoint's delivery log for the first failure.\n2. Endpoints are disabled after 3 days of failures; deliveries older than 24 hours are not retried.\n"
         "3. Tell the customer to re-enable it and backfill with GET /v2/invoices?updated_since=."),
        ("runbook-rate-limit-requests", "Runbook: rate limit increase requests", "2026-05-20",
         "Per-minute limits are 60 (Starter), 300 (Professional), 1,000 (Enterprise). Only Enterprise can get a custom limit, approved by the CSM and platform team. "
         "The concurrency limit of 10 is never raised."),
        ("runbook-dst-check", "Runbook: DST change week checklist", "2025-10-20",
         "Before each DST change on 2.1.x to 2.3.0: watch recurring invoice volume per hour; compare against the same day last week. (Not needed after 2.3.1.)"),
    ]
    for name, title, d, body in runbooks:
        md(name, title, "runbook", d, body, owner="support-eng")

    # Release engineering notes for every version
    for v, d in ALL_RELEASES:
        fixed = [b for b in B.values() if b["fixed_in_version"] == v]
        found = [b for b in B.values() if b["affected_version"] == v]
        lines = [f"- {b['bug_id']}: {b['title']} ({b['severity']})" for b in fixed] or ["- None"]
        flines = [f"- {b['bug_id']}: {b['title']} ({b['status']})" for b in found] or ["- None"]
        md(f"release-retro-{v}", f"Release retro: {v}", "release_retro", d,
           f"Release {v} went out on {d}.\n\n## Fixed in this release\n" + "\n".join(lines) +
           "\n\n## Bugs first seen on this version\n" + "\n".join(flines) +
           "\n\n## Notes\nRollout was staged over 3 days: 10%, 50%, 100% of organizations.", owner="release-eng")

    # Misc internal notes
    misc = [
        ("note-auto-match-tolerance", "Note: auto-match tolerance", "2026-05-02", "design_note",
         "Auto-match requires an exact amount match and a date within 7 days. We tried a 0.5% tolerance in beta and it caused false matches on recurring payments of similar size, so it was removed before 2.3.0."),
        ("note-bulk-limit", "Note: why bulk actions cap at 100", "2026-01-15", "design_note",
         "Bulk actions run synchronously in the browser request. 100 invoices keeps the request under 30 seconds. An older prototype used 50; some community posts still repeat that number."),
        ("note-sandbox", "Note: sandbox reset job", "2026-02-10", "design_note",
         "The sandbox is wiped at 00:00 UTC on the first day of each month. Keys (ip_test_) survive the reset; data does not."),
        ("note-sso", "Note: SSO status", "2026-09-15", "planning",
         "SAML SSO is not scheduled. It has been requested by many Enterprise prospects. Sales must not promise a date."),
        ("note-classic-sunset", "Note: Classic sunset", "2025-06-15", "planning",
         "All Classic (1.x) organizations moved to 2.0.0 between 2025-06-10 and 2025-06-14. Classic help pages stay online for reference but are no longer updated."),
        ("note-x-ratelimit", "Note: rate limit headers", "2026-05-12", "design_note",
         "Since 2.3.0 every v2 response includes X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset. Concurrency (IP-4291) has no header; clients learn it from the 429."),
        ("note-webhook-ordering", "Note: webhook ordering", "2026-06-18", "design_note",
         "We don't guarantee ordering. invoice.paid can arrive before payment.created. Consumers should fetch the object by id when order matters."),
        ("note-pdf-workaround", "Note: long invoice workaround for support", "2026-09-01", "runbook",
         "For BUG-2310-02, tell customers to send the invoice link. Do not suggest splitting invoices unless the customer asks; it changes their numbering."),
    ]
    for name, title, d, kind, body in misc:
        md(name, title, kind, d, body)
    return docs


# ---------------------------------------------------------------------------
# Sales enablement (DOCX)
# ---------------------------------------------------------------------------

def sales_docs():
    S = []

    def doc(name, title, updated, owner, blocks, status="published"):
        S.append(dict(name=name, title=title, updated=updated, owner=owner, status=status, blocks=blocks))

    comp = {
        "LedgerLoop": ("Mid-market accounting suite", "Strong general ledger and payroll", "Weak API (no webhooks), multi-currency costs extra",
                       ["Multi-currency on every plan", "API v2 with webhooks on Professional and Enterprise", "Client portal included"]),
        "BillBright": ("Invoicing app for freelancers", "Very simple, cheap single-user plan", "No bank reconciliation auto-match, no custom reports",
                       ["Bank feeds with auto-match (2.3.0+)", "Custom report builder", "Bulk actions on up to 100 invoices"]),
        "FinchBooks": ("Accounting for small businesses", "Popular with accountants, many integrations", "Per-feature add-ons make it expensive; audit log only on top tier",
                       ["Simple per-seat pricing: $12, $25, $40", "Audit log on Enterprise (13 months)", "Recurring invoices on every plan"]),
    }
    for c, (what, strength, weak, wins) in comp.items():
        doc(f"battlecard-{c.lower()}", f"Battlecard: InvoicePilot vs {c}", "2026-08-20", "product-marketing", [
            ("h2", "Who they are"), ("p", f"{c}: {what}."),
            ("h2", "Where they're strong"), ("p", strength + "."),
            ("h2", "Where they're weak"), ("p", weak + "."),
            ("h2", "How we win"), ("ul", wins),
            ("h2", "Traps to avoid"), ("ul", ["Don't promise SSO. It's not available and has no date.",
                                              "Don't promise fix dates for open bugs.",
                                              "Custom roles are Enterprise only."]),
        ])
    # stale battlecard with old facts (planted conflict)
    doc("battlecard-ledgerloop-2025", "Battlecard: InvoicePilot vs LedgerLoop (2025)", "2025-08-12", "product-marketing", [
        ("h2", "How we win"),
        ("ul", ["Multi-currency on every plan", "Bank feeds sync once a day on every plan",
                "Professional includes 5 bank feeds", "API v1 is our recommended API"]),
        ("p", "Use this card for deals closing in 2025."),
    ], status="archived")
    doc("plan-comparison-for-reps", "Plan comparison for sales reps", "2026-06-01", "sales-ops", [
        ("p", "Use this table on calls. Prices are list prices per seat per year."),
        ("table", ["Limit", "Starter", "Professional", "Enterprise"], [
            ["Price per seat per year", "$12", "$25", "$40"],
            ["API requests per minute", "60", "300", "1,000"],
            ["Concurrent API requests", "10", "10", "10"],
            ["Connected bank feeds", "2", "10", "Unlimited"],
            ["Webhook endpoints", "None", "5", "25"],
            ["Custom invoice templates", "No (3 standard)", "Yes", "Yes"],
            ["Portal branding", "No", "Yes", "Yes"],
            ["Scheduled report emails", "No", "Yes", "Yes"],
            ["Saved custom reports", "10", "100", "Unlimited"],
            ["Custom user roles", "No", "No", "Yes"],
            ["Audit log", "No", "No", "13 months"],
            ["Support", "Email, 2 business days", "Email and chat, 1 business day", "Priority, 4 hours, named CSM"]]),
    ])
    doc("discount-policy", "Discount and approval policy", "2026-02-01", "sales-ops", [
        ("p", "Reps can discount up to 10% on their own. 11% to 20% needs a sales manager. Above 20% needs the VP of Sales."),
        ("table", ["Seats", "Standard volume discount"], [["1-49", "None"], ["50-199", "10%"], ["200+", "15%"]]),
        ("p", "Multi-year prepay adds 5%. Discounts never apply to added seats mid-term; those are full price for their own 12-month term."),
        ("p", "Never share another customer's discount."),
    ])
    doc("objection-handling", "Objection handling", "2026-07-10", "sales-enablement", [
        ("h3", "\"We need SSO.\""), ("p", "SAML SSO isn't available. Don't give a date. Offer two-step verification and the security overview."),
        ("h3", "\"Your API is rate limited.\""), ("p", "Enterprise gets 1,000 requests per minute and can ask for a custom limit. Webhooks remove most polling."),
        ("h3", "\"We heard about bugs in 2.3.1.\""), ("p", "Be honest: BUG-2310-01 and BUG-2310-02 are open with workarounds. Don't promise a fix date."),
        ("h3", "\"Starter is too limited.\""), ("p", "Starter has every feature; plans differ by limits. Show the plan comparison."),
        ("h3", "\"Can we pay monthly?\""), ("p", "Seats are billed per year. There's no monthly billing."),
    ])
    industries = [("manufacturing", "Manufacturing", "multi-currency invoicing for overseas buyers, bank feeds, and the aged receivables report"),
                  ("professional-services", "Professional services", "recurring retainers, estimates that convert to invoices, and time-saving bulk actions"),
                  ("nonprofit", "Nonprofits", "simple per-seat pricing, the audit log on Enterprise, and statements for donors and grantees"),
                  ("food-beverage", "Food and beverage", "high invoice volume with bulk actions and multi-currency for imports"),
                  ("technology", "Technology companies", "API v2, webhooks, and SDKs for Python and Node.js"),
                  ("real-estate", "Real estate", "recurring invoices for rent, the client portal, and ACH payments")]
    for slug, name, pitch in industries:
        doc(f"one-pager-{slug}", f"Industry one-pager: {name}", "2026-05-15", "product-marketing", [
            ("p", f"For {name.lower()}, lead with {pitch}."),
            ("h2", "Discovery questions"),
            ("ul", ["How many invoices do you send each month?", "Do you bill in more than one currency?",
                    "How do you reconcile your bank today?", "Do you need an API or integrations?"]),
            ("h2", "Proof points"), ("p", "Use reference customers only with their permission. Check with your CSM first."),
        ])
    doc("whats-new-2-3-for-sales", "What's new in 2.3.x for sales", "2026-08-20", "product-marketing", [
        ("ul", ["2.3.0: bank reconciliation auto-match and the custom report builder",
                "2.3.0: bank feeds sync every 4 hours instead of once a day",
                "2.3.0: report exports to CSV, XLSX, and PDF",
                "2.3.1: recurring invoices use UTC, fixing skipped cycles",
                "Known issues in 2.3.1: BUG-2310-01 (multi-currency auto-match), BUG-2310-02 (long invoice PDFs), BUG-2310-03 (cosmetic)"]),
        ("p", "Webhooks are generally available since 2026-06-15 on Professional and Enterprise."),
    ])
    doc("demo-script", "Demo script (30 minutes)", "2026-06-20", "sales-enablement", [
        ("ol", ["Dashboard (2 min)", "Create and send a multi-currency invoice (5 min)", "Client portal: view and pay (5 min)",
                "Bank feeds and auto-match (5 min). Use a base-currency account; avoid foreign-currency accounts on 2.3.1.",
                "Custom report builder (5 min). Keep the date range under 3 years.", "Questions (8 min)"]),
    ])
    doc("security-faq-for-sales", "Security FAQ for sales", "2026-04-20", "security", [
        ("h3", "Is data encrypted?"), ("p", "Yes, TLS 1.2+ in transit and AES-256 at rest."),
        ("h3", "Do you have SOC 2?"), ("p", "Yes, SOC 2 Type II. Share the report under NDA."),
        ("h3", "Where is data hosted?"), ("p", "US or EU, chosen at signup."),
        ("h3", "SSO?"), ("p", "Not available. No date."),
        ("h3", "Audit log?"), ("p", "Enterprise only, 13 months of history."),
    ])
    doc("migration-from-competitors", "Migrating customers from other tools", "2026-03-01", "onboarding", [
        ("p", "Import clients and open invoices from CSV. Historical invoices can be imported as paid."),
        ("p", "Expense CSV import accepts DD/MM/YYYY dates since 2.2.1."),
        ("p", "For API-based migrations, use API v2 with Idempotency-Key on every POST so a re-run doesn't create duplicates."),
    ])
    doc("sales-faq", "Sales FAQ", "2026-09-05", "sales-enablement", [
        ("h3", "Can Starter customers use multi-currency?"), ("p", "Yes, every plan."),
        ("h3", "How many invoices in a bulk action?"), ("p", "Up to 100."),
        ("h3", "Do you have late fees?"), ("p", "Not automatic. Classic had them; 2.x does not."),
        ("h3", "What's the current version?"), ("p", "2.3.1 (Aurora Patch 1), released 2026-08-14."),
        ("h3", "When is 2.4.0?"), ("p", "No public date. Don't share internal targets."),
    ])
    doc("pricing-sheet-2025", "Pricing sheet (2025)", "2025-06-10", "sales-ops", [
        ("table", ["Plan", "Price per seat per year"], [["Starter", "$10"], ["Professional", "$22"], ["Enterprise", "$36"]]),
        ("p", "Launch pricing for 2.0.0. Valid until 2025-12-31."),
    ], status="archived")
    doc("pricing-sheet-2026", "Pricing sheet (2026)", "2026-01-05", "sales-ops", [
        ("table", ["Plan", "Price per seat per year"], [["Starter", "$12"], ["Professional", "$25"], ["Enterprise", "$40"]]),
        ("p", "Valid from 2026-01-01."),
    ])
    doc("draft-roles-messaging", "Draft: roles and permissions messaging", "2025-10-03", "product-marketing", [
        ("p", "Professional and Enterprise customers can create custom roles to control exactly who sees what."),
        ("p", "DRAFT, not reviewed."),
    ], status="draft")
    doc("enterprise-onboarding", "Enterprise onboarding checklist", "2026-04-01", "customer-success", [
        ("ol", ["Kickoff with the named CSM", "Set up custom roles and invite users (invite links expire after 7 days)",
                "Connect bank feeds (unlimited on Enterprise)", "Set up webhooks (up to 25 endpoints)",
                "Review the audit log settings (13 months of history)"]),
    ])
    doc("renewal-playbook", "Renewal playbook", "2026-05-01", "customer-success", [
        ("p", "Start renewal talks 90 days before the term ends. Added seats have their own 12-month term, so a customer can have several renewal dates."),
        ("p", "Downgrades take effect at renewal. Check limits first: Starter allows 2 bank feeds and no webhooks."),
    ])
    doc("api-pitch", "Pitching the API to technical buyers", "2026-08-10", "sales-engineering", [
        ("ul", ["REST API v2 with cursor pagination and JSON error codes like IP-4220",
                "Idempotency-Key on every POST so retries are safe",
                "Webhooks with HMAC signatures (X-InvoicePilot-Signature)",
                "SDKs for Python (pip install invoicepilot) and Node.js (@invoicepilot/node)",
                "Sandbox with ip_test_ keys, reset monthly"]),
        ("p", "API v1 still works with no shutoff date."),
    ])
    doc("competitive-pricing-notes", "Competitive pricing notes", "2026-07-01", "sales-ops", [
        ("table", ["Vendor", "Entry price", "Notes"], [
            ["InvoicePilot", "$12/seat/year", "All features on every plan; limits differ"],
            ["LedgerLoop", "Higher", "Multi-currency is an add-on"],
            ["BillBright", "Lower", "Single-user focus, no auto-match"],
            ["FinchBooks", "Similar", "Many paid add-ons"]]),
        ("p", "Don't quote competitor prices as exact; they change often."),
    ])
    return S


def write_docx(path, d):
    from docx import Document
    from docx.shared import Pt
    doc = Document()
    cp = doc.core_properties
    cp.title = d["title"]
    cp.author = d["owner"]
    cp.subject = "sales_enablement"
    cp.keywords = f"status={d['status']}"
    cp.comments = f"last_updated={d['updated']}"
    doc.add_heading(d["title"], level=1)
    p = doc.add_paragraph(f"Owner: {d['owner']} · Last updated: {d['updated']} · Status: {d['status']}")
    p.runs[0].font.size = Pt(9)
    p = doc.add_paragraph("Internal: for InvoicePilot sales and customer success only.")
    p.runs[0].font.size = Pt(9)
    for b in d["blocks"]:
        k = b[0]
        if k in ("h2", "h3"):
            doc.add_heading(b[1], level=2 if k == "h2" else 3)
        elif k == "p":
            doc.add_paragraph(b[1])
        elif k in ("ul", "ol"):
            for item in b[1]:
                doc.add_paragraph(item, style="List Bullet" if k == "ul" else "List Number")
        elif k == "table":
            t = doc.add_table(rows=1, cols=len(b[1]))
            t.style = "Table Grid"
            for i, h in enumerate(b[1]):
                t.rows[0].cells[i].text = h
            for r in b[2]:
                cells = t.add_row().cells
                for i, c in enumerate(r):
                    cells[i].text = c
    doc.save(path)


# ---------------------------------------------------------------------------
# Release notes PDFs, same layout as v1 so the v1 PDF parser works
# ---------------------------------------------------------------------------

def write_release_pdfs(out_dir, B):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)
    st = getSampleStyleSheet()
    st.add(ParagraphStyle(name="H1C", parent=st["Heading1"], spaceAfter=6))
    st.add(ParagraphStyle(name="H2C", parent=st["Heading2"], spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1F3864")))
    st.add(ParagraphStyle(name="Meta", parent=st["Normal"], textColor=colors.grey, spaceAfter=12))
    st.add(ParagraphStyle(name="Body", parent=st["Normal"], spaceAfter=6, leading=14))
    st.add(ParagraphStyle(name="Cell", parent=st["Normal"], fontSize=8.5, leading=11))
    st.add(ParagraphStyle(name="CellH", parent=st["Normal"], fontSize=8.5, leading=11, textColor=colors.white, fontName="Helvetica-Bold"))

    def bullets(items):
        return ListFlowable([ListItem(Paragraph(i, st["Body"])) for i in items], bulletType="bullet", start="circle", leftIndent=18)

    for version, codename, released, _ in NEW_VERSIONS:
        c = PATCH_COPY[version]
        s = [Paragraph(f"InvoicePilot Release Notes &mdash; v{version} “{codename}”", st["H1C"]),
             Paragraph(f"Released {released}", st["Meta"]), Paragraph(c["headline"], st["Body"]), Spacer(1, 10)]
        if c["new"]:
            s += [Paragraph("New Features", st["H2C"]), bullets(c["new"])]
        if c["imp"]:
            s += [Paragraph("Improvements", st["H2C"]), bullets(c["imp"])]
        fixed = [b for b in B.values() if b["fixed_in_version"] == version]
        if fixed:
            s.append(Paragraph("Fixed in This Release", st["H2C"]))
            for b in fixed:
                s.append(Paragraph(f"<b>{b['bug_id']}</b> &mdash; {b['title']}", st["Body"]))
                s.append(Paragraph(b["description"], st["Body"]))
        open_ = [b for b in B.values() if b["affected_version"] == version and b["status"] in ("Open", "Won't Fix")]
        if open_:
            s.append(Paragraph("Known Issues", st["H2C"]))
            rows = [[Paragraph(h, st["CellH"]) for h in ["Bug ID", "Severity", "Status", "Description"]]]
            rows += [[Paragraph(b[k], st["Cell"]) for k in ("bug_id", "severity", "status", "description")] for b in open_]
            t = Table(rows, colWidths=[1.1 * inch, 0.65 * inch, 0.55 * inch, 3.5 * inch], repeatRows=1)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0"))]))
            s += [t, Spacer(1, 6)]
        s += [Paragraph("Upgrade Notes", st["H2C"]), Paragraph(c["upgrade"], st["Body"])]
        path = out_dir / f"InvoicePilot_Release_Notes_v{version}.pdf"
        SimpleDocTemplate(str(path), pagesize=letter, topMargin=0.9 * inch, bottomMargin=0.8 * inch,
                          leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                          title=f"InvoicePilot Release Notes v{version}").build(s)


# ---------------------------------------------------------------------------
# Answer key (NEVER ingest)
# ---------------------------------------------------------------------------

def answer_key(wrong_log):
    rows = "\n".join(f"| {t} | {k} | {r} |" for t, k, r in wrong_log)
    return f"""# Corpus v2 answer key

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
{rows}

## v1 questions whose answer grows in v2
- h-15 (which API errors to retry): v2 adds retryable subcodes IP-4091 (after 1 second), IP-4291 (after Retry-After), and IP-5031 (with backoff), on api/api-error-subcodes.
- Questions about "every release" or "all known bugs" now need the patch releases and bugs_v2.csv.

## Facts still NOT in the public docs
- A shutoff date for API v1
- A committed fix date for BUG-2310-01/02/03 or BUG-2300-01 (only an internal tentative target exists)
- SSO/SAML timelines
- Any customer's discount (the general discount policy is in sales/discount-policy.docx)
"""


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="folder with the v1 CSVs (data_package)")
    ap.add_argument("--out", default="corpus")
    ap.add_argument("--key", default="answer_key")
    args = ap.parse_args()

    with open(Path(args.data) / "bugs.csv", newline="") as f:
        B = {b["bug_id"]: b for b in csv.DictReader(f)}
    with open(Path(args.data) / "customers.csv", newline="") as f:
        customers = list(csv.DictReader(f))
    cols = ["bug_id", "title", "affected_version", "fixed_in_version", "severity", "status", "reported_date", "description"]
    for row in NEW_BUGS:
        assert row[0] not in B, f"bug id clash: {row[0]}"
        B[row[0]] = dict(zip(cols, row))

    out, key = Path(args.out), Path(args.key)
    existing = {p.relative_to(out) for p in out.rglob("*") if p.is_file()} if out.exists() else set()

    # help center
    A = []

    def art(section, slug, title, updated, body, type="help_article", applies=None, plans=None, related=None, author=None):
        A.append(dict(section=section, slug=slug, id=f"{section}/{slug}", title=title, updated=updated, body=body,
                      type=type, applies=applies, plans=plans, related=related, author=author))

    api_pages(art)
    help_pages(art, B)
    legacy_pages(art)
    for slug, title, author, d, paras in COMMUNITY:
        art("community", slug, title, d, [("p", p) for p in paras], type="community", author=author)

    written = []

    def write(rel, data, binary=False):
        rel = Path(rel)
        if rel in existing:
            raise SystemExit(f"refusing to overwrite a v1 file: {rel}")
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        (p.write_bytes if binary else lambda t: p.write_text(t, encoding="utf-8"))(data)
        written.append(rel)

    ids = [a["id"] for a in A]
    assert len(ids) == len(set(ids)), "duplicate article ids"
    for a in A:
        write(f"help_center/{a['section']}/{a['slug']}.html", render_page(a))

    wrong_log = []
    for t in make_tickets(customers, wrong_log, B):
        write(f"support_tickets/{t['ticket_id']}.json", json.dumps(t, indent=2, ensure_ascii=False) + "\n")

    for name, text in eng_docs(B):
        write(f"engineering/{name}.md", text)

    (out / "sales").mkdir(parents=True, exist_ok=True)
    for d in sales_docs():
        rel = Path(f"sales/{d['name']}.docx")
        if rel in existing:
            raise SystemExit(f"refusing to overwrite a v1 file: {rel}")
        write_docx(out / rel, d)
        written.append(rel)

    rn = out / "release_notes"
    rn.mkdir(parents=True, exist_ok=True)
    for v, *_ in NEW_VERSIONS:
        if Path(f"release_notes/InvoicePilot_Release_Notes_v{v}.pdf") in existing:
            raise SystemExit(f"refusing to overwrite release notes v{v}")
    write_release_pdfs(rn, B)
    written += [Path(f"release_notes/InvoicePilot_Release_Notes_v{v}.pdf") for v, *_ in NEW_VERSIONS]

    key.mkdir(parents=True, exist_ok=True)
    (key / "corpus_v2_key.md").write_text(answer_key(wrong_log), encoding="utf-8")
    with open(key / "bugs_v2.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for b in sorted(B.values(), key=lambda b: b["bug_id"]):
            w.writerow(b)

    from collections import Counter
    by = Counter(p.parts[0] if p.parts[0] != "help_center" else f"help_center/{p.parts[1]}" for p in written)
    print(f"corpus v2: wrote {len(written)} new files")
    for k, n in sorted(by.items()):
        print(f"  {k:32s} {n}")
    print(f"answer key: {key / 'corpus_v2_key.md'}, {key / 'bugs_v2.csv'}")


if __name__ == "__main__":
    main()
