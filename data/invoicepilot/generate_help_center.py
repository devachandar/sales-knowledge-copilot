"""
Generate the InvoicePilot help center: ~75 HTML pages that agree with the CSVs.

Usage:
    python generate_help_center.py --data path/to/data_package --out corpus

Writes:
    corpus/help_center/<section>/<slug>.html   help articles, API reference, FAQ
    answer_key/planted_conflicts.md            NEVER ingest this; it is for your evals
    answer_key/plan_limits.csv                 the plan facts the docs state, for tests

Design rules this script follows:
  * Versions, dates, bug IDs, plans and prices come from the CSVs, not from memory.
  * Every plan can use every feature (the usage logs prove it), so plans differ
    only by LIMITS: API rate limits, bank feeds, templates, branding, schedules.
  * A few conflicts are planted ON PURPOSE (stale pages, a low-authority community
    page). Each one is listed in answer_key/planted_conflicts.md with the right answer.
  * Pages look like a crawled website: nav, breadcrumbs, footer, feedback widget.
    Cleaning that boilerplate and pulling out metadata is your Day 3 job.
  * Metadata is realistic, not perfect: some pages have no "applies to" or no
    plan info, and community pages have no meta tags at all.
"""

import argparse
import csv
import html
import os
import random
from pathlib import Path

random.seed(42)

# ---------------------------------------------------------------------------
# Load the source of truth
# ---------------------------------------------------------------------------

def load(data_dir):
    def rows(name):
        with open(Path(data_dir) / name, newline="") as f:
            return list(csv.DictReader(f))
    versions = rows("product_versions.csv")
    bugs = {b["bug_id"]: b for b in rows("bugs.csv")}
    sales = rows("sales_records.csv")
    prices = {}
    for s in sales:
        prices[s["plan"]] = int(s["unit_price_usd"])
    return {v["version"]: v for v in versions}, bugs, prices


# ---------------------------------------------------------------------------
# Plan limits. These are NEW facts the docs introduce. None of them conflict
# with the data: every plan uses every feature; plans differ only in limits.
# ---------------------------------------------------------------------------

PLANS = ["Starter", "Professional", "Enterprise"]

PLAN_LIMITS = [
    # (limit, Starter, Professional, Enterprise)
    ("API rate limit (requests per minute)", "60", "300", "1,000"),
    ("Connected bank feeds", "2", "10", "Unlimited"),
    ("Invoice templates", "3 standard templates", "Custom templates", "Custom templates"),
    ("Client portal branding (logo and accent color)", "No", "Yes", "Yes"),
    ("Scheduled report emails", "No", "Yes", "Yes"),
    ("Saved custom reports", "10", "100", "Unlimited"),
    ("Custom user roles", "No", "No", "Yes"),
    ("Audit log", "No", "No", "Yes (13 months)"),
    ("Support", "Email, 2 business days", "Email and chat, 1 business day", "Priority, 4 hours, named CSM"),
]


# ---------------------------------------------------------------------------
# Tiny markup helpers. A body is a list of blocks:
#   ("p", text) ("h2", text) ("h3", text) ("ul", [items]) ("ol", [items])
#   ("table", [header], [[row], ...]) ("code", text) ("note", text) ("warn", text)
# ---------------------------------------------------------------------------

def esc(t):
    return html.escape(t, quote=False)


def render_blocks(blocks):
    out = []
    for b in blocks:
        kind = b[0]
        if kind == "p":
            out.append(f"<p>{esc(b[1])}</p>")
        elif kind in ("h2", "h3"):
            out.append(f"<{kind}>{esc(b[1])}</{kind}>")
        elif kind in ("ul", "ol"):
            items = "".join(f"<li>{esc(i)}</li>" for i in b[1])
            out.append(f"<{kind}>{items}</{kind}>")
        elif kind == "table":
            head = "".join(f"<th>{esc(h)}</th>" for h in b[1])
            body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in b[2])
            out.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
        elif kind == "code":
            out.append(f"<pre><code>{esc(b[1])}</code></pre>")
        elif kind == "note":
            out.append(f'<div class="callout note"><strong>Note:</strong> {esc(b[1])}</div>')
        elif kind == "warn":
            out.append(f'<div class="callout warning"><strong>Known issue:</strong> {esc(b[1])}</div>')
        else:
            raise ValueError(kind)
    return "\n".join(out)


SECTION_NAMES = {
    "getting-started": "Getting Started",
    "invoicing": "Invoicing",
    "multi-currency": "Multi-Currency",
    "recurring-invoices": "Recurring Invoices",
    "expenses": "Expenses",
    "estimates": "Estimates",
    "client-portal": "Client Portal",
    "bank-reconciliation": "Bank Reconciliation",
    "reports": "Reports",
    "account-billing": "Account & Billing",
    "api": "Developer API",
    "support": "Support",
    "community": "Community",
}

NAV = " | ".join(SECTION_NAMES[s] for s in SECTION_NAMES if s != "community")

FOOTER = (
    '<footer><p>&copy; 2026 InvoicePilot, Inc. All rights reserved. '
    '<a href="/privacy">Privacy</a> · <a href="/terms">Terms</a> · <a href="/status">Status</a></p>'
    '<div class="cookie-banner">We use cookies to improve your experience. '
    '<button>Accept all</button> <button>Manage preferences</button></div></footer>'
)

FEEDBACK = (
    '<div class="feedback">Was this article helpful? <button>Yes</button> <button>No</button> '
    '<span>1,204 people found this helpful</span></div>'
)


def render_page(a):
    meta = [f'<meta name="doc-id" content="{a["id"]}">']
    if a["type"] != "community":
        meta.append(f'<meta name="source-type" content="{a["type"]}">')
        meta.append(f'<meta name="last-updated" content="{a["updated"]}">')
        if a.get("applies"):
            meta.append(f'<meta name="applies-to-version" content="{a["applies"]}">')
        if a.get("plans"):
            meta.append(f'<meta name="available-on-plans" content="{", ".join(a["plans"])}">')
    section = SECTION_NAMES[a["section"]]
    crumbs = f'<nav class="breadcrumb">Help Center &gt; {esc(section)} &gt; {esc(a["title"])}</nav>'

    header_bits = []
    if a["type"] == "community":
        header_bits.append(f'<p class="byline">Posted by {esc(a["author"])} on {a["updated"]} · Community answer, not reviewed by InvoicePilot staff</p>')
    else:
        header_bits.append(f'<p class="updated">Last updated: {a["updated"]}</p>')
        if a.get("applies"):
            header_bits.append(f'<p class="applies">Applies to: InvoicePilot {esc(a["applies"])}</p>')
        if a.get("plans"):
            header_bits.append(f'<p class="plans">Available on: {esc(", ".join(a["plans"]))}</p>')

    related = ""
    if a.get("related"):
        links = "".join(f'<li><a href="{r}.html">{r}</a></li>' for r in a["related"])
        related = f'<aside class="related"><h4>Related articles</h4><ul>{links}</ul></aside>'

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
{crumbs}
<main>
<article>
<h1>{esc(a["title"])}</h1>
{chr(10).join(header_bits)}
{render_blocks(a["body"])}
</article>
{related}
{FEEDBACK if a["type"] != "community" else ""}
</main>
{FOOTER}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Article content
# ---------------------------------------------------------------------------

def build_articles(V, BUGS, PRICES):
    A = []

    def art(section, slug, title, updated, body, type="help_article",
            applies=None, plans=None, related=None, author=None):
        A.append(dict(section=section, slug=slug, id=f"{section}/{slug}", title=title,
                      updated=updated, body=body, type=type, applies=applies,
                      plans=plans, related=related, author=author))

    def bug(bid):
        b = BUGS[bid]
        return b

    rel = {v: V[v]["release_date"] for v in V}
    ALL = PLANS
    PRO_UP = ["Professional", "Enterprise"]

    # ---------------- Getting started ----------------
    art("getting-started", "welcome", "Welcome to InvoicePilot", "2026-08-14", [
        ("p", "InvoicePilot is online invoicing and accounting software for small and mid-sized businesses. "
              "You can send invoices, track expenses, reconcile bank accounts, and give clients a self-serve portal."),
        ("h2", "What you can do"),
        ("ul", ["Create and send invoices in any supported currency",
                "Schedule recurring invoices that generate and send automatically",
                "Record expenses and scan receipts",
                "Send estimates and convert them to invoices",
                "Connect bank feeds and reconcile transactions",
                "Build custom reports and export them",
                "Integrate with other systems through the REST API"]),
        ("h2", "Current version"),
        ("p", f"The current version is 2.3.1 \"{V['2.3.1']['codename']}\", released {rel['2.3.1']}. "
              "See Version history for every release."),
    ], applies="2.3.1", related=["create-organization", "navigation"])

    art("getting-started", "create-organization", "Create your organization", "2025-06-20", [
        ("p", "Your organization holds your company profile, base currency, fiscal year, and users."),
        ("ol", ["Sign up at app.invoicepilot.example and verify your email.",
                "Enter your company name, country, and industry.",
                "Choose your base currency. This cannot be changed after your first transaction.",
                "Set your fiscal year start month.",
                "Choose a plan: Starter, Professional, or Enterprise."]),
        ("note", "Your base currency is the currency your reports are shown in. To bill in other currencies, "
                 "enable multi-currency later under Settings > Currencies."),
    ], applies="2.0.0+", plans=ALL, related=["enable-multi-currency", "plans-and-limits"])

    art("getting-started", "invite-users", "Invite users and assign seats", "2026-02-03", [
        ("p", "Each person who signs in to InvoicePilot uses one seat. You can invite as many users as you have seats."),
        ("ol", ["Go to Settings > Users.",
                "Click Invite User and enter their email.",
                "Pick a role: Admin, Accountant, Staff, or Read-only.",
                "Click Send Invite. The invite link expires after 7 days."]),
        ("p", "If you run out of seats, an account owner can buy more from Settings > Subscription > Add Seats."),
        ("note", "Custom roles beyond the four built-in roles are available on the Enterprise plan only."),
    ], applies="2.0.0+", plans=ALL, related=["seats-and-add-seats", "roles-and-audit-log"])

    art("getting-started", "navigation", "Finding your way around", "2025-06-12", [
        ("p", "Version 2.0.0 introduced a redesigned navigation. The left sidebar holds Dashboard, Sales "
              "(Invoices, Estimates, Recurring Invoices, Customers), Purchases (Expenses), Banking, Reports, and Settings."),
        ("p", "Organization preferences such as currencies, taxes, invoice templates, and users all live under Settings."),
    ], applies="2.0.0+")

    art("getting-started", "dashboard", "Understanding the dashboard", "2025-06-30", [
        ("p", "The dashboard gives an at-a-glance view of revenue, outstanding invoices, and expense trends."),
        ("h2", "Widgets"),
        ("ul", ["Total receivables, split into current and overdue",
                "Income and expense chart for the last 12 months",
                "Top 5 expense categories",
                "Cash flow by bank account"]),
        ("h2", "Large accounts"),
        ("p", f"In early 2.0.0 builds, accounts with more than 500 contacts saw a blank dashboard "
              f"({bug('BUG-2000-02')['bug_id']}). This was fixed within version 2.0.0."),
    ], applies="2.0.0+", plans=ALL)

    # ---------------- Invoicing ----------------
    art("invoicing", "create-invoice", "Create and send an invoice", "2026-01-22", [
        ("ol", ["Go to Sales > Invoices and click New Invoice.",
                "Pick a customer. Their currency and payment terms fill in automatically.",
                "Add line items with quantity, rate, and tax.",
                "Choose a template.",
                "Click Save and Send to email it, or Save as Draft."]),
        ("p", "Invoice numbers follow your prefix and sequence, set under Settings > Invoices. The default is INV-000001."),
        ("p", "Search covers invoice numbers and line-item descriptions."),
    ], applies="2.0.0+", plans=ALL, related=["invoice-templates", "line-items-and-long-invoices", "tax-rates"])

    art("invoicing", "invoice-templates", "Invoice templates", "2026-03-15", [
        ("p", "Templates control how your invoice PDF looks: layout, fonts, logo, and which fields appear."),
        ("table", ["Plan", "Templates"], [["Starter", "3 standard templates"],
                                          ["Professional", "Standard templates plus custom templates"],
                                          ["Enterprise", "Standard templates plus custom templates"]]),
        ("h2", "Creating a custom template"),
        ("ol", ["Go to Settings > Templates > Invoices.",
                "Click New Custom Template and start from a standard one.",
                "Edit the header, columns, footer, and colors.",
                "Save and set it as default if you like."]),
        ("p", "Since 2.0.0, invoice PDFs with custom templates render about 2x faster than before."),
        ("note", "Starter customers asking for a custom template need to move to Professional or Enterprise."),
    ], applies="2.0.0+", plans=ALL, related=["export-invoice-pdf", "plans-and-limits"])

    b = bug("BUG-2310-02")
    art("invoicing", "line-items-and-long-invoices", "Line items and long invoices", "2026-09-01", [
        ("p", "An invoice can have up to 500 line items. Each line has an item, description, quantity, rate, discount, and tax."),
        ("h2", "Long invoices in PDF"),
        ("warn", f"{b['bug_id']} ({b['severity']}, {b['status']}): {b['description']} Affects {b['affected_version']}."),
        ("h3", "Workaround"),
        ("ul", ["Send the invoice by email link instead of attaching the PDF. The online view shows every line.",
                "Or group related lines so the invoice has 25 line items or fewer.",
                "The client portal view is not affected."]),
    ], applies="2.3.1", plans=ALL, related=["export-invoice-pdf", "known-issues"])

    art("invoicing", "invoice-search", "Search invoices", "2025-06-15", [
        ("p", "Use the search bar on the Invoices list. Since 2.0.0, search covers line-item descriptions as well as invoice numbers."),
        ("ul", ["Search by invoice number: INV-000123",
                "Search by customer name",
                "Search by any word in a line-item description",
                "Filter by status: Draft, Sent, Overdue, Paid, Void"]),
    ], applies="2.0.0+", plans=ALL)

    art("invoicing", "bulk-invoice-actions", "Bulk invoice actions", "2026-01-21", [
        ("p", "From the Invoices list you can select several invoices and act on all of them at once."),
        ("h2", "Supported actions"),
        ("ul", ["Send", "Send payment reminder", "Void", "Mark as sent", "Export as PDF (zipped)"]),
        ("h2", "Limits"),
        ("p", "You can select up to 100 invoices per bulk action. To act on more, filter the list and repeat."),
        ("p", "Bulk actions were added in version 2.2.0."),
    ], applies="2.2.0+", plans=ALL, related=["payment-reminders"])

    art("invoicing", "void-or-delete-invoice", "Void or delete an invoice", "2025-07-08", [
        ("p", "Draft invoices can be deleted. Sent invoices cannot be deleted; void them instead so your records stay complete."),
        ("ol", ["Open the invoice.", "Click More > Void.", "Enter a reason. The reason is kept with the invoice."]),
        ("p", "Voided invoices stay in reports with a zero balance and show a VOID watermark."),
    ], applies="2.0.0+", plans=ALL)

    art("invoicing", "tax-rates", "Add a new tax rate", "2025-08-02", [
        ("ol", ["Go to Settings > Taxes.",
                "Click New Tax Rate.",
                "Enter a name (for example, NY Sales Tax) and a percentage.",
                "Optionally group rates into a tax group, like state plus county.",
                "Save. The rate is now available on invoice and estimate line items."]),
        ("p", "Changing a tax rate only affects new invoices. Existing invoices keep the rate they were created with."),
    ], applies="2.0.0+", plans=ALL)

    art("invoicing", "payment-reminders", "Payment reminders", "2025-09-20", [
        ("p", "Version 2.1.0 added client-level payment reminders with configurable send windows."),
        ("ol", ["Go to Settings > Reminders to set defaults: for example 3 days before due, on the due date, and 7 days after.",
                "Pick a send window, such as weekdays 9:00 to 17:00 in the client's timezone.",
                "Override per client from the customer's page."]),
        ("p", "Since 2.2.0 you can also send reminders in bulk from the Invoices list."),
    ], applies="2.1.0+", plans=ALL, related=["bulk-invoice-actions"])

    art("invoicing", "export-invoice-pdf", "Export invoices as PDF", "2026-09-01", [
        ("p", "Open an invoice and click PDF > Download, or select several and use the bulk Export as PDF action."),
        ("warn", f"In {BUGS['BUG-2310-02']['affected_version']}, invoices with more than 25 line items export as a single page "
                 f"and drop the remaining lines ({BUGS['BUG-2310-02']['bug_id']}). See Line items and long invoices for a workaround."),
    ], applies="2.0.0+", plans=ALL, related=["line-items-and-long-invoices"])

    # ---------------- Multi-currency ----------------
    art("multi-currency", "enable-multi-currency", "Enable multi-currency", "2025-06-10", [
        ("p", "Multi-currency invoicing arrived in 2.0.0. It lets you bill customers in their own currency."),
        ("ol", ["Go to Settings > Currencies.",
                "Turn on Multi-currency.",
                "Add the currencies you need.",
                "Set each customer's currency on their profile."]),
        ("note", "Existing single-currency organizations are not affected until multi-currency is turned on."),
    ], applies="2.0.0+", plans=ALL, related=["exchange-rates", "zero-decimal-currencies"])

    art("multi-currency", "exchange-rates", "Exchange rates", "2025-06-18", [
        ("p", "InvoicePilot updates exchange rates once a day from a market data provider. You can also enter a rate by hand on any invoice."),
        ("p", "Reports convert foreign amounts to your base currency using the rate saved on each transaction."),
    ], applies="2.0.0+", plans=ALL)

    b = bug("BUG-2000-01")
    art("multi-currency", "zero-decimal-currencies", "Zero-decimal currencies (JPY, KRW, and others)", "2025-09-18", [
        ("p", "Some currencies, like Japanese yen and Korean won, have no decimal places."),
        ("h2", "Rounding fix"),
        ("p", f"{b['bug_id']}: {b['description']} It affected {b['affected_version']} and was fixed in {b['fixed_in_version']}."),
        ("p", "If you issued invoices in a zero-decimal currency on 2.0.0, review them for 1-unit overcharges per line item."),
    ], applies="2.0.0+", plans=ALL, related=["known-issues"])

    b = bug("BUG-2310-01")
    art("multi-currency", "multi-currency-bank-reconciliation", "Multi-currency accounts and bank reconciliation", "2026-08-27", [
        ("p", "If your bank feed is in a currency different from your invoices, InvoicePilot must convert amounts before matching."),
        ("warn", f"{b['bug_id']} ({b['severity']}, {b['status']}): {b['description']} Affects {b['affected_version']}."),
        ("h3", "Workaround"),
        ("ul", ["Use manual matching for foreign-currency transactions until a fix ships.",
                "Base-currency transactions still auto-match normally.",
                "Do not bulk-confirm suggested matches on multi-currency accounts; review each one."]),
    ], applies="2.3.1", plans=ALL, related=["auto-match", "manual-reconciliation"])

    # ---------------- Recurring invoices ----------------
    art("recurring-invoices", "set-up-recurring-invoices", "Set up recurring invoices", "2025-09-17", [
        ("p", "Recurring invoices were added in 2.1.0. They generate and send an invoice on a schedule."),
        ("ol", ["Go to Sales > Recurring Invoices > New.",
                "Choose the customer and line items.",
                "Pick a cadence: daily, weekly, monthly, or custom.",
                "Set a start date and an optional end date.",
                "Choose whether to send automatically or save as draft for review."]),
        ("p", "Before you confirm, the preview shows the next 3 scheduled send dates."),
    ], applies="2.1.0+", plans=ALL, related=["recurring-invoice-timezones", "skipped-recurring-cycle"])

    art("recurring-invoices", "recurring-cadences", "Recurring cadences explained", "2025-10-01", [
        ("table", ["Cadence", "Example"], [["Daily", "Every day at 06:00"],
                                           ["Weekly", "Every Monday"],
                                           ["Monthly", "The 1st of every month, or the last day of the month"],
                                           ["Custom", "Every 2 weeks, every 3 months, or every N days"]]),
        ("p", "If a monthly schedule falls on a day that does not exist, like February 30, the invoice goes out on the last day of that month."),
    ], applies="2.1.0+", plans=ALL)

    # CURRENT timezone article (2.3.1)
    art("recurring-invoices", "recurring-invoice-timezones", "How recurring invoice schedules handle time zones", "2026-08-14", [
        ("p", "Starting in 2.3.1, recurring invoice schedules are calculated in UTC internally. "
              "Send times are still shown in your organization's local time zone."),
        ("p", f"This change fixed {BUGS['BUG-2100-02']['bug_id']}, where schedules calculated in local time skipped a cycle "
              "when daylight-saving time shifted."),
        ("p", "No action is needed. Existing schedules were migrated automatically when 2.3.1 rolled out."),
    ], applies="2.3.1+", plans=ALL, related=["skipped-recurring-cycle"])

    # STALE timezone article (planted conflict #2)
    art("recurring-invoices", "recurring-schedule-local-time", "Recurring invoices use your local time zone", "2025-10-12", [
        ("p", "Recurring invoice schedules are calculated in your organization's local time zone, set under Settings > Organization."),
        ("p", "If you change your organization's time zone, future send dates are recalculated."),
        ("p", "We are aware that some customers have reported a missed cycle around daylight-saving changes. We are investigating."),
    ], applies="2.1.0", plans=ALL)

    b = bug("BUG-2100-02")
    art("recurring-invoices", "skipped-recurring-cycle", "Troubleshooting: a recurring invoice skipped a cycle", "2026-08-15", [
        ("p", f"Cause: {b['bug_id']}, \"{b['title']}\". {b['description']}"),
        ("p", f"Affected versions: {b['affected_version']} through 2.3.0. Fixed in {b['fixed_in_version']}."),
        ("h2", "If you are on 2.3.1"),
        ("p", "The fix is already applied. To recover a missed invoice from before the fix, open the recurring profile and click Create Missed Invoice."),
        ("h2", "If you are on an older version"),
        ("p", "Upgrade to 2.3.x. As a stopgap, avoid schedules that send between 01:00 and 03:00 local time on DST change days."),
    ], applies="2.1.0+", plans=ALL, related=["recurring-invoice-timezones", "known-issues"])

    # ---------------- Expenses ----------------
    art("expenses", "record-an-expense", "Record an expense", "2025-07-01", [
        ("ol", ["Go to Purchases > Expenses > New.",
                "Enter date, amount, vendor, and category.",
                "Optionally mark it billable and link it to a customer.",
                "Attach a receipt image or PDF."]),
        ("p", "Since 2.1.0 you can bulk-reassign expense categories from the expenses list."),
    ], applies="2.0.0+", plans=ALL, related=["receipt-scanning"])

    b = bug("BUG-2100-01")
    art("expenses", "receipt-scanning", "Scan receipts", "2025-10-02", [
        ("p", "Added in 2.1.0. Take a photo of a receipt in the mobile app, or upload one, and InvoicePilot extracts the vendor, date, and amount."),
        ("h2", "Accuracy"),
        ("p", "Typed and printed receipts scan reliably. Always check the extracted amount before saving."),
        ("warn", f"{b['bug_id']} ({b['status']}): {b['description']}"),
    ], applies="2.1.0+", plans=ALL, related=["record-an-expense"])

    art("expenses", "expense-categories", "Manage expense categories", "2025-09-22", [
        ("p", "Go to Settings > Expense Categories to add, rename, or archive categories."),
        ("p", "To move many expenses at once, select them in the expenses list and click Change Category. This bulk action was added in 2.1.0."),
    ], applies="2.1.0+", plans=ALL)

    # ---------------- Estimates ----------------
    art("estimates", "create-estimate", "Create and send an estimate", "2025-07-10", [
        ("p", "Estimates, also called quotes, let you send a price before you do the work."),
        ("ol", ["Go to Sales > Estimates > New.", "Add the customer and line items.", "Set an expiry date.", "Send it."]),
        ("p", "Clients can accept or decline from the email or the client portal."),
    ], applies="2.0.0+", plans=ALL, related=["convert-estimate"])

    art("estimates", "convert-estimate", "Convert an estimate to an invoice", "2025-07-10", [
        ("p", "Open an accepted estimate and click Convert to Invoice. All line items, taxes, and notes carry over."),
        ("p", "You can convert one estimate into several invoices for staged billing, for example 50% up front and 50% on completion."),
    ], applies="2.0.0+", plans=ALL)

    # ---------------- Client portal ----------------
    art("client-portal", "client-portal-overview", "Client Portal 2.0 overview", "2026-01-20", [
        ("p", "Version 2.2.0 introduced Client Portal 2.0, a single self-serve page where your clients can:"),
        ("ul", ["View their full invoice history", "Download statements", "Pay online", "Accept or decline estimates"]),
        ("p", "Existing portal links from earlier versions keep working with no changes."),
    ], applies="2.2.0+", plans=ALL, related=["portal-branding", "customer-statements"])

    art("client-portal", "portal-branding", "Brand your client portal", "2026-01-25", [
        ("p", "Add your logo and accent color so the portal matches your brand."),
        ("p", "Go to Settings > Client Portal > Branding."),
        ("note", "Portal branding is available on Professional and Enterprise. Starter portals use the default InvoicePilot look."),
    ], applies="2.2.0+", plans=PRO_UP)

    art("client-portal", "customer-statements", "Customer statements", "2026-02-10", [
        ("p", "A statement lists a customer's invoices, payments, and balance for a date range."),
        ("h2", "For one customer"),
        ("p", "Open the customer and click Statement. Download as PDF or email it. Clients can also download their own statements from the portal."),
        ("h2", "For many customers"),
        ("p", "There is no bulk statement export in the app today. Two options:"),
        ("ul", ["Use the custom report builder (2.3.0+) with the Customer Balance report and export to XLSX.",
                "Use API v2: GET /v2/customers/{customer_id}/statements for each customer."]),
    ], applies="2.2.0+", plans=ALL, related=["custom-report-builder", "api-customers"])

    b = bug("BUG-2200-01")
    art("client-portal", "safari-login-loop", "Troubleshooting: client portal login loop on Safari", "2026-01-28", [
        ("p", f"{b['bug_id']}: {b['description']}"),
        ("p", f"This affected {b['affected_version']} and was fixed in a hotfix within {b['fixed_in_version']}. No action needed."),
        ("p", "If a client still sees the loop, ask them to clear cookies for portal.invoicepilot.example and sign in again."),
    ], applies="2.2.0", plans=ALL)

    # ---------------- Bank reconciliation ----------------
    art("bank-reconciliation", "connect-bank-feed", "Connect a bank feed", "2026-05-12", [
        ("ol", ["Go to Banking > Add Bank Account.", "Search for your bank and sign in through the secure connection.",
                "Pick which accounts to connect.", "Choose how far back to import, up to 90 days."]),
        ("table", ["Plan", "Connected bank feeds"], [["Starter", "2"], ["Professional", "10"], ["Enterprise", "Unlimited"]]),
    ], applies="2.0.0+", plans=ALL, related=["bank-feed-sync", "auto-match"])

    # CURRENT sync article
    art("bank-reconciliation", "bank-feed-sync", "How often bank feeds sync", "2026-05-11", [
        ("p", "Since 2.3.0, connected bank feeds sync every 4 hours. Before 2.3.0 they synced once a day."),
        ("p", "Click Refresh Feed on any bank account to sync on demand, up to 5 times per day."),
    ], applies="2.3.0+", plans=ALL)

    # STALE sync article (planted conflict #3)
    art("bank-reconciliation", "bank-feed-faq", "Bank feeds: frequently asked questions", "2025-11-04", [
        ("h3", "How often do bank feeds update?"),
        ("p", "Bank feeds sync once a day, usually overnight. Transactions from today will appear tomorrow."),
        ("h3", "Can I connect a credit card?"),
        ("p", "Yes. Credit cards connect the same way as bank accounts."),
        ("h3", "Is my bank login stored?"),
        ("p", "No. The connection uses a read-only token from your bank. InvoicePilot never sees your password."),
    ], applies="2.0.0+", plans=ALL)

    art("bank-reconciliation", "auto-match", "Bank reconciliation auto-match", "2026-05-11", [
        ("p", "Added in 2.3.0. Auto-match compares incoming bank transactions with recorded invoices and expenses and suggests matches."),
        ("h2", "How matching works"),
        ("ul", ["Amount must match exactly", "Date must be within 5 days", "Payee or reference text raises confidence"]),
        ("p", "Auto-match runs the first time you open Bank Reconciliation after upgrading. Review suggested matches before confirming them in bulk."),
        ("warn", f"On {BUGS['BUG-2310-01']['affected_version']}, auto-match does not convert foreign-currency amounts "
                 f"({BUGS['BUG-2310-01']['bug_id']}, {BUGS['BUG-2310-01']['severity']}). See Multi-currency accounts and bank reconciliation."),
    ], applies="2.3.0+", plans=ALL, related=["manual-reconciliation", "multi-currency-bank-reconciliation"])

    art("bank-reconciliation", "manual-reconciliation", "Reconcile transactions manually", "2025-08-15", [
        ("p", "Manual reconciliation has been available since 2.0.0 and is still the fallback when auto-match cannot find a match."),
        ("ol", ["Go to Banking and open the account.", "Click an uncategorized transaction.",
                "Choose Match to pick an existing invoice or expense, or Categorize to record a new one.",
                "When the statement balance and InvoicePilot balance agree, click Finish Reconciliation."]),
    ], applies="2.0.0+", plans=ALL, related=["auto-match"])

    art("bank-reconciliation", "review-suggested-matches", "Review and confirm suggested matches", "2026-05-20", [
        ("p", "Suggested matches show a confidence label: High, Medium, or Low."),
        ("ul", ["High: amount, date, and reference all match", "Medium: amount and date match", "Low: amount matches only"]),
        ("p", "You can confirm all High matches in one click. Medium and Low matches should be checked one at a time."),
        ("p", "Undo a confirmed match from the transaction's history within 30 days."),
    ], applies="2.3.0+", plans=ALL, related=["auto-match"])

    # ---------------- Reports ----------------
    art("reports", "standard-reports", "Standard reports", "2025-06-25", [
        ("p", "InvoicePilot includes standard reports on every plan:"),
        ("ul", ["Profit and Loss", "Balance Sheet", "Cash Flow", "Aged Receivables",
                "Sales by Customer", "Expenses by Category", "Customer Balance", "Tax Summary"]),
    ], applies="2.0.0+", plans=ALL, related=["custom-report-builder"])

    art("reports", "custom-report-builder", "Custom report builder", "2026-08-16", [
        ("p", "Added in 2.3.0. Build a report from any combination of accounts, date ranges, and tags, then save it."),
        ("table", ["Plan", "Saved custom reports"], [["Starter", "10"], ["Professional", "100"], ["Enterprise", "Unlimited"]]),
        ("p", "In 2.3.1, the report builder got faster for accounts with 10,000+ transactions."),
        ("warn", f"{BUGS['BUG-2300-01']['bug_id']} ({BUGS['BUG-2300-01']['status']}): {BUGS['BUG-2300-01']['description']}"),
    ], applies="2.3.0+", plans=ALL, related=["report-schedules", "large-date-ranges", "report-exports"])

    art("reports", "report-schedules", "Schedule report emails", "2026-05-11", [
        ("p", "Saved reports can be emailed to stakeholders on a recurring basis: daily, weekly, or monthly."),
        ("p", "Open a saved report and click Schedule. Add recipients, including people outside your organization."),
        ("note", "Scheduled report emails are available on Professional and Enterprise."),
    ], applies="2.3.0+", plans=PRO_UP)

    art("reports", "report-exports", "Export a report", "2026-05-11", [
        ("p", "Since 2.3.0, every report can be exported as CSV, XLSX, or PDF from the same report view."),
        ("p", "Before 2.3.0, reports exported to PDF and CSV only."),
    ], applies="2.0.0+", plans=ALL)

    b = bug("BUG-2300-01")
    art("reports", "large-date-ranges", "Troubleshooting: report times out on long date ranges", "2026-05-22", [
        ("p", f"{b['bug_id']}: {b['description']} Status: {b['status']}. Affects {b['affected_version']} and later."),
        ("h2", "Workaround"),
        ("ul", ["Split the report into ranges of 3 years or less and combine the exports.",
                "Or use API v2, which pages through results with a cursor."]),
    ], applies="2.3.0+", plans=ALL, related=["custom-report-builder", "api-pagination"])

    b = bug("BUG-2310-03")
    art("reports", "date-picker-week-start", "Date picker shows the wrong first day of the week", "2026-09-03", [
        ("p", f"{b['bug_id']} ({b['severity']}): {b['description']}"),
        ("p", "This is cosmetic. Report data is correct. Type dates directly into the range fields if the calendar is confusing."),
    ], applies="2.3.1")

    # ---------------- Account & billing ----------------
    price_rows = [[p, f"${PRICES[p]}"] for p in PLANS]
    art("account-billing", "plans-and-limits", "Compare plans", "2026-05-15", [
        ("p", "All plans include every feature: invoicing, expenses, estimates, recurring invoices, multi-currency, "
              "client portal, bank reconciliation, reports, and the API. Plans differ in limits and extras."),
        ("h2", "List price"),
        ("table", ["Plan", "Price per seat per year (USD)"], price_rows),
        ("h2", "Limits"),
        ("table", ["", *PLANS], [list(r) for r in PLAN_LIMITS]),
        ("note", "Prices shown are list prices. Your contract may differ. Contact your account manager about your own agreement."),
    ], applies="2.3.0+", related=["seats-and-add-seats", "sso-saml"])

    art("account-billing", "seats-and-add-seats", "Seats and adding seats", "2026-03-02", [
        ("p", "InvoicePilot is billed per seat per year. One seat lets one user sign in."),
        ("h2", "Adding seats"),
        ("p", "Account owners can add seats from Settings > Subscription > Add Seats. Added seats are billed at the plan's full per-seat price "
              "and start their own 12-month term from the day you add them. They are not prorated."),
        ("h2", "Removing seats"),
        ("p", "Seats can be reduced at renewal. Unused seats are not refunded mid-term."),
    ], plans=ALL, related=["renewals", "plans-and-limits"])

    art("account-billing", "renewals", "Renewals and license expiry", "2026-03-02", [
        ("p", "Every license runs for 12 months from its order date. You can see each license's expiry date under Settings > Subscription."),
        ("p", "Licenses renew for another 12 months when you place a Renewal order. We email the account owner 60, 30, and 7 days before expiry."),
        ("p", "If a license expires, users on those seats lose sign-in access. Data is kept for 90 days."),
    ], plans=ALL, related=["seats-and-add-seats"])

    art("account-billing", "how-updates-roll-out", "How new versions roll out", "2026-08-14", [
        ("p", "InvoicePilot uses version numbers of the form major.minor.patch, for example 2.3.1."),
        ("table", ["Release type", "Example", "How you get it"], [
            ["Major or minor", "2.2.0 to 2.3.0", "Your account owner chooses when to upgrade, from Settings > Subscription > Upgrade"],
            ["Patch", "2.3.0 to 2.3.1", "Rolled out automatically to every organization on that line. No action needed"],
        ]),
        ("p", "Upgrades between minor versions are free on every plan."),
    ], plans=ALL, related=["version-history"])

    art("account-billing", "sso-saml", "Single sign-on (SSO) and SAML", "2026-04-02", [
        ("p", "InvoicePilot does not support SSO or SAML sign-in on any plan today."),
        ("p", "Users sign in with email and password, and you can require two-factor authentication for everyone under Settings > Security."),
        ("p", "If SSO is important to you, tell your account manager so your request is counted."),
    ], applies="2.2.0+", plans=ALL)

    art("account-billing", "roles-and-audit-log", "User roles and the audit log", "2026-02-03", [
        ("table", ["Role", "Can do"], [["Admin", "Everything, including users and billing"],
                                       ["Accountant", "All transactions and reports, no user management"],
                                       ["Staff", "Create invoices, estimates, and expenses"],
                                       ["Read-only", "View only"]]),
        ("p", "Enterprise organizations can build custom roles and see an audit log of every change, kept for 13 months."),
    ], plans=ALL)

    art("account-billing", "export-your-data", "Export all your data", "2025-12-01", [
        ("p", "Admins can export all organization data from Settings > Data > Export. You get a ZIP with one CSV per record type."),
        ("p", "Exports are usually ready within an hour. You will get an email with a download link that expires in 7 days."),
    ], plans=ALL)

    # ---------------- API ----------------
    art("api", "api-overview", "API overview: v1 and v2", "2026-01-20", [
        ("p", "InvoicePilot has two REST APIs."),
        ("table", ["", "API v1", "API v2"], [
            ["Status", "Legacy (still available)", "Current"],
            ["Base URL", "https://api.invoicepilot.example/v1", "https://api.invoicepilot.example/v2"],
            ["Pagination", "page and per_page", "Cursor-based"],
            ["Introduced", "2.0.0", "2.2.0"]]),
        ("p", "New integrations should use v2. Existing v1 integrations keep working and do not need to migrate right away."),
    ], type="api_reference", applies="2.2.0+", plans=ALL, related=["api-authentication", "migrate-v1-to-v2"])

    # STALE API page (planted conflict #4)
    art("api", "api-quickstart-2025", "API quickstart", "2025-07-14", [
        ("p", "The InvoicePilot API is the recommended way to integrate with InvoicePilot. All endpoints live under https://api.invoicepilot.example/v1."),
        ("code", "curl https://api.invoicepilot.example/v1/invoices?page=1&per_page=50 \\\n  -H \"Authorization: Bearer YOUR_API_KEY\""),
        ("p", "Use page and per_page to page through results. The maximum per_page is 200."),
    ], type="api_reference", applies="2.0.0+", plans=ALL)

    art("api", "api-authentication", "Authentication", "2026-01-20", [
        ("p", "Create an API key under Settings > Developer > API Keys. Send it as a bearer token."),
        ("code", "curl https://api.invoicepilot.example/v2/invoices \\\n  -H \"Authorization: Bearer ip_live_xxxxxxxxxxxx\""),
        ("p", "Keys start with ip_live_ for production and ip_test_ for the sandbox. Keys can be scoped to read-only."),
    ], type="api_reference", applies="2.2.0+", plans=ALL)

    b = bug("BUG-2200-02")
    art("api", "api-rate-limits", "Rate limits", "2026-05-11", [
        ("p", "Rate limits are per organization, counted per minute."),
        ("table", ["Plan", "Requests per minute"], [["Starter", "60"], ["Professional", "300"], ["Enterprise", "1,000"]]),
        ("h2", "Headers"),
        ("p", "Every v2 response includes:"),
        ("ul", ["X-RateLimit-Limit: your limit per minute",
                "X-RateLimit-Remaining: requests left in this window",
                "X-RateLimit-Reset: Unix time when the window resets"]),
        ("p", "When you go over, you get HTTP 429 with error code IP-4290 and a Retry-After header in seconds."),
        ("p", f"Note: in {b['affected_version']} these headers were missing ({b['bug_id']}). Fixed in {b['fixed_in_version']}."),
        ("h2", "Need more?"),
        ("p", "Higher limits come with a higher plan. Enterprise customers can ask their CSM about a custom limit."),
    ], type="api_reference", applies="2.3.0+", plans=ALL, related=["api-errors"])

    art("api", "api-pagination", "Pagination (v2)", "2026-01-20", [
        ("p", "List endpoints in v2 return up to 100 items and a next_cursor. Pass it back as ?cursor= to get the next page. "
              "When next_cursor is null you have reached the end."),
        ("code", "GET /v2/invoices?limit=100\n{\n  \"data\": [...],\n  \"next_cursor\": \"eyJpZCI6IjEyMzQ1In0\"\n}"),
    ], type="api_reference", applies="2.2.0+", plans=ALL)

    art("api", "api-errors", "Error codes", "2026-05-11", [
        ("p", "Errors return JSON with an HTTP status, a code, and a message."),
        ("code", "{\n  \"error\": {\n    \"code\": \"IP-4220\",\n    \"message\": \"line_items[3].quantity must be greater than 0\"\n  }\n}"),
        ("table", ["HTTP", "Code", "Meaning", "Retry?"], [
            ["400", "IP-4000", "Malformed request or invalid JSON", "No"],
            ["401", "IP-4010", "Missing or invalid API key", "No"],
            ["403", "IP-4030", "Key lacks permission, or the limit for your plan is reached", "No"],
            ["404", "IP-4040", "Resource not found", "No"],
            ["409", "IP-4090", "Idempotency-Key was reused with a different request body", "No"],
            ["422", "IP-4220", "Validation failed; see message", "No"],
            ["429", "IP-4290", "Rate limit exceeded; wait for Retry-After", "Yes"],
            ["500", "IP-5000", "Internal error", "Yes, with backoff"],
            ["503", "IP-5030", "Bank feed provider unavailable", "Yes, with backoff"]]),
        ("h2", "Idempotency"),
        ("p", "Send an Idempotency-Key header on POST requests. Retrying with the same key returns the original result instead of creating a duplicate. Keys are kept for 24 hours."),
    ], type="api_reference", applies="2.2.0+", plans=ALL, related=["api-rate-limits"])

    art("api", "api-invoices", "Invoices endpoint", "2026-01-20", [
        ("table", ["Method", "Path", "Does"], [
            ["GET", "/v2/invoices", "List invoices. Filters: status, customer_id, date_from, date_to"],
            ["POST", "/v2/invoices", "Create an invoice"],
            ["GET", "/v2/invoices/{invoice_id}", "Get one invoice"],
            ["PATCH", "/v2/invoices/{invoice_id}", "Update a draft invoice"],
            ["POST", "/v2/invoices/{invoice_id}/send", "Email the invoice"],
            ["POST", "/v2/invoices/{invoice_id}/void", "Void the invoice"]]),
        ("code", "POST /v2/invoices\nIdempotency-Key: 7f9c2e1a\n{\n  \"customer_id\": \"cus_8812\",\n  \"currency\": \"EUR\",\n  \"line_items\": [{\"description\": \"Consulting\", \"quantity\": 10, \"rate\": 150}]\n}"),
    ], type="api_reference", applies="2.2.0+", plans=ALL)

    art("api", "api-customers", "Customers endpoint", "2026-02-10", [
        ("table", ["Method", "Path", "Does"], [
            ["GET", "/v2/customers", "List customers"],
            ["POST", "/v2/customers", "Create a customer"],
            ["GET", "/v2/customers/{customer_id}", "Get one customer"],
            ["GET", "/v2/customers/{customer_id}/statements", "Get a statement. Params: date_from, date_to, format=pdf|json"]]),
    ], type="api_reference", applies="2.2.0+", plans=ALL)

    art("api", "api-payments", "Payments endpoint", "2026-01-20", [
        ("table", ["Method", "Path", "Does"], [
            ["GET", "/v2/payments", "List payments"],
            ["POST", "/v2/payments", "Record a payment against one or more invoices"],
            ["DELETE", "/v2/payments/{payment_id}", "Delete a payment and reopen the invoices"]]),
        ("p", "Payments made through the client portal are created automatically and appear here."),
    ], type="api_reference", applies="2.2.0+", plans=ALL)

    art("api", "migrate-v1-to-v2", "Migrate from API v1 to v2", "2026-02-15", [
        ("table", ["Change", "v1", "v2"], [
            ["Base path", "/v1", "/v2"],
            ["Pagination", "?page=2&per_page=50", "?cursor=...&limit=100"],
            ["Errors", "Plain text message", "JSON with IP- error codes"],
            ["Rate limit headers", "None", "X-RateLimit-* (from 2.3.0)"],
            ["Idempotency", "Not supported", "Idempotency-Key header"]]),
        ("ol", ["Create a new v2 key or reuse your v1 key; both work.",
                "Switch list calls to cursor pagination.",
                "Update error handling to read error.code.",
                "Add Idempotency-Key to POST calls so retries are safe."]),
        ("p", "There is no shutoff date for v1 yet. We will give at least 12 months' notice."),
    ], type="api_reference", applies="2.2.0+", plans=ALL, related=["api-overview", "api-errors"])

    # ---------------- Support (some generated from CSVs) ----------------
    vrows = [[v, V[v]["codename"], V[v]["release_date"], V[v]["summary"]] for v in sorted(V, key=lambda s: tuple(map(int, s.split("."))))]
    art("support", "version-history", "Version history", "2026-08-14", [
        ("table", ["Version", "Codename", "Released", "Summary"], vrows),
        ("p", "Full details for each version are in its release notes."),
    ], type="guide", related=["how-updates-roll-out", "known-issues"])

    krows = [[b["bug_id"], b["title"], b["affected_version"], b["fixed_in_version"] or "—", b["severity"], b["status"]]
             for b in BUGS.values()]
    art("support", "known-issues", "Known issues and fixes", "2026-09-03", [
        ("p", "Every tracked issue, the version it affects, and where it was fixed."),
        ("table", ["Bug ID", "Title", "Affects", "Fixed in", "Severity", "Status"], krows),
    ], type="guide", related=["version-history"])

    art("support", "contact-support", "Contact support", "2026-03-01", [
        ("table", ["Plan", "Channels", "First response target"], [
            ["Starter", "Email", "2 business days"],
            ["Professional", "Email and chat", "1 business day"],
            ["Enterprise", "Priority email, chat, phone, named CSM", "4 hours"]]),
        ("p", "Critical issues on Enterprise, such as a Critical-severity bug, are handled 24/7."),
    ], type="guide", plans=ALL)

    art("support", "faq", "Frequently asked questions", "2026-06-01", [
        ("h3", "Can I bill in more than one currency?"),
        ("p", "Yes, on every plan. Turn on multi-currency under Settings > Currencies."),
        ("h3", "Do you support SSO?"),
        ("p", "Not today. See Single sign-on (SSO) and SAML."),
        ("h3", "How do I add a tax rate?"),
        ("p", "Settings > Taxes > New Tax Rate."),
        ("h3", "Can I get a custom invoice template?"),
        ("p", "Yes, on Professional and Enterprise. Starter includes 3 standard templates."),
        ("h3", "Can I raise my API rate limit?"),
        ("p", "Limits are set by plan: 60, 300, or 1,000 requests per minute. Enterprise customers can ask about a custom limit."),
        ("h3", "Are added seats prorated?"),
        ("p", "No. Added seats are billed at the full per-seat price and start their own 12-month term."),
        ("h3", "How do I export statements for all customers?"),
        ("p", "There is no bulk statement export in the app. Use the Customer Balance report or API v2."),
    ], type="faq", plans=ALL)

    art("support", "glossary", "Glossary", "2025-08-01", [
        ("table", ["Term", "Meaning"], [
            ["Seat", "One user license, billed per year"],
            ["Base currency", "The currency your reports use"],
            ["Bank feed", "A live connection that imports transactions from your bank"],
            ["Auto-match", "Automatic pairing of bank transactions with invoices or expenses (2.3.0+)"],
            ["Recurring profile", "The schedule behind a recurring invoice"],
            ["Statement", "A summary of a customer's invoices, payments, and balance"],
            ["Patch release", "A release like 2.3.1 that only fixes issues and rolls out automatically"]]),
    ], type="guide")

    # ---------------- Community (low authority, planted conflict #5) ----------------
    art("community", "bulk-send-tips", "Tip: bulk-sending invoices at month end", "2026-02-11", [
        ("p", "We send about 300 invoices at month end. Bulk actions only let you pick 50 at a time, so filter by customer group and do it in batches of 50."),
        ("p", "Also, do the payment reminders the same way. Works fine for us."),
    ], type="community", author="ledger_lucy")

    art("community", "reconciliation-euro-workaround", "Auto-match ignoring our EUR account?", "2026-09-05", [
        ("p", "Since 2.3.1 our EUR feed barely matches anything. Support says it's a known bug. "
              "We switched the EUR account to manual matching for now and it's fine, just slower."),
        ("p", "Reply: same here with GBP. Didn't hear when the fix is coming."),
    ], type="community", author="finops_dan")

    art("community", "api-v1-still-works", "Is API v1 going away?", "2026-03-20", [
        ("p", "Our integration still uses v1 and it works fine after the 2.2.0 update. Docs say v1 is legacy but there's no shutdown date."),
    ], type="community", author="dev_priyanka")

    return A


# ---------------------------------------------------------------------------
# Answer key: planted conflicts + data mismatches. NEVER INGEST.
# ---------------------------------------------------------------------------

ANSWER_KEY = """# Answer key: planted conflicts and data mismatches

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
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="folder with the CSVs (data_package)")
    ap.add_argument("--out", default="corpus")
    ap.add_argument("--key", default="answer_key")
    args = ap.parse_args()

    V, BUGS, PRICES = load(args.data)
    articles = build_articles(V, BUGS, PRICES)

    ids = [a["id"] for a in articles]
    assert len(ids) == len(set(ids)), "duplicate article ids"

    out = Path(args.out) / "help_center"
    for a in articles:
        p = out / a["section"] / f"{a['slug']}.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_page(a), encoding="utf-8")

    key = Path(args.key)
    key.mkdir(parents=True, exist_ok=True)
    (key / "planted_conflicts.md").write_text(ANSWER_KEY, encoding="utf-8")
    with open(key / "plan_limits.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["limit", *PLANS])
        w.writerows(PLAN_LIMITS)
        w.writerow(["List price per seat per year (USD)", *[PRICES[p] for p in PLANS]])

    by_section = {}
    for a in articles:
        by_section[a["section"]] = by_section.get(a["section"], 0) + 1
    print(f"Wrote {len(articles)} pages to {out}")
    for s, n in by_section.items():
        print(f"  {s:22s} {n}")
    print(f"Answer key in {key}/ (do not ingest)")


if __name__ == "__main__":
    main()
