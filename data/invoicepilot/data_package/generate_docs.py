import csv
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, ListFlowable, ListItem)

DATA = "/home/claude/data"
DOCS_OUT = "/home/claude/data/docs"
os.makedirs(DOCS_OUT, exist_ok=True)

with open(f"{DATA}/product_versions.csv") as f:
    versions = list(csv.DictReader(f))

with open(f"{DATA}/bugs.csv") as f:
    bugs = list(csv.DictReader(f))

FEATURE_COPY = {
    "2.0.0": {
        "headline": "A redesigned core app with native multi-currency support.",
        "new_features": [
            "Multi-currency invoicing: bill customers in their local currency with daily exchange-rate updates.",
            "New dashboard with at-a-glance revenue, outstanding invoices, and expense trends.",
            "Redesigned navigation and settings area for faster access to organization preferences.",
        ],
        "improvements": [
            "Invoice PDF rendering is now roughly 2x faster for accounts with custom templates.",
            "Search now covers invoice line-item descriptions, not just invoice numbers.",
        ],
        "upgrade_notes": "Existing single-currency organizations are unaffected; multi-currency must be "
                          "enabled explicitly under Settings > Currencies before it appears on new invoices.",
    },
    "2.1.0": {
        "headline": "Automated recurring invoices and receipt scanning for expenses.",
        "new_features": [
            "Recurring Invoices: schedule invoices to auto-generate and send on a daily, weekly, monthly, "
            "or custom cadence.",
            "Expense receipt scanning: snap a photo of a receipt and InvoicePilot extracts the vendor, "
            "date, and amount automatically.",
            "Client-level payment reminders with configurable send windows.",
        ],
        "improvements": [
            "Recurring invoice previews now show the next 3 scheduled send dates before you confirm.",
            "Expense categories can now be bulk-reassigned from the expenses list.",
        ],
        "upgrade_notes": "Recurring invoice schedules created in 2.1.0 are calculated in your organization's "
                          "local timezone; see Known Issues below for a daylight-saving edge case.",
    },
    "2.2.0": {
        "headline": "A redesigned client portal, bulk invoice actions, and API v2.",
        "new_features": [
            "Client Portal 2.0: clients can view invoice history, download statements, and pay online "
            "from a single self-serve page.",
            "Bulk invoice actions: send, remind, or void up to 100 invoices at once from the invoice list.",
            "API v2 (REST): new endpoints for invoices, customers, and payments with cursor-based pagination.",
        ],
        "improvements": [
            "Client portal now supports organization branding (logo and accent color).",
            "API v1 remains available but is now considered legacy; new integrations should use v2.",
        ],
        "upgrade_notes": "Existing client portal links continue to work without changes. API v1 integrations "
                          "are not affected and do not need to migrate immediately.",
    },
    "2.3.0": {
        "headline": "Automatic bank-reconciliation matching and a custom report builder.",
        "new_features": [
            "Bank Reconciliation auto-match: connected bank feeds are automatically matched against "
            "recorded invoices and expenses.",
            "Custom Report Builder: build and save reports by combining any combination of accounts, "
            "date ranges, and tags.",
            "Saved report schedules can now be emailed to stakeholders on a recurring basis.",
        ],
        "improvements": [
            "Bank feed sync frequency increased from once daily to every 4 hours.",
            "Report exports now support CSV, XLSX, and PDF from the same report view.",
        ],
        "upgrade_notes": "Auto-match runs automatically the first time you open Bank Reconciliation after "
                          "upgrading; review suggested matches before confirming them in bulk.",
    },
    "2.3.1": {
        "headline": "Patch release: recurring-invoice timezone fix and PDF export corrections.",
        "new_features": [],
        "improvements": [
            "Recurring invoices now use UTC internally for schedule calculation, resolving missed cycles "
            "around daylight-saving changes (see Fixed in This Release).",
            "Minor performance improvements to the custom report builder for accounts with 10,000+ "
            "transactions.",
        ],
        "upgrade_notes": "This is a patch release. No action is required to receive it; it is rolled out "
                          "automatically to all organizations on the 2.3.x line.",
    },
}

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="H1Custom", parent=styles["Heading1"], spaceAfter=6))
styles.add(ParagraphStyle(name="H2Custom", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6,
                           textColor=colors.HexColor("#1F3864")))
styles.add(ParagraphStyle(name="MetaStyle", parent=styles["Normal"], textColor=colors.grey, spaceAfter=12))
styles.add(ParagraphStyle(name="BodyCustom", parent=styles["Normal"], spaceAfter=6, leading=14))
styles.add(ParagraphStyle(name="CellText", parent=styles["Normal"], fontSize=8.5, leading=11))
styles.add(ParagraphStyle(name="CellHeader", parent=styles["Normal"], fontSize=8.5, leading=11,
                           textColor=colors.white, fontName="Helvetica-Bold"))

SEV_COLOR = {
    "Critical": colors.HexColor("#B00020"),
    "High": colors.HexColor("#C05621"),
    "Medium": colors.HexColor("#946C00"),
    "Low": colors.HexColor("#4A5568"),
}

def bullet_list(items):
    return ListFlowable(
        [ListItem(Paragraph(i, styles["BodyCustom"])) for i in items],
        bulletType="bullet", start="circle", leftIndent=18,
    )

for v in versions:
    version = v["version"]
    copy = FEATURE_COPY[version]
    story = []

    story.append(Paragraph(f"InvoicePilot Release Notes &mdash; v{version} \u201c{v['codename']}\u201d",
                            styles["H1Custom"]))
    story.append(Paragraph(f"Released {v['release_date']}", styles["MetaStyle"]))
    story.append(Paragraph(copy["headline"], styles["BodyCustom"]))
    story.append(Spacer(1, 10))

    if copy["new_features"]:
        story.append(Paragraph("New Features", styles["H2Custom"]))
        story.append(bullet_list(copy["new_features"]))

    if copy["improvements"]:
        story.append(Paragraph("Improvements", styles["H2Custom"]))
        story.append(bullet_list(copy["improvements"]))

    fixed_here = [b for b in bugs if b["fixed_in_version"] == version]
    if fixed_here:
        story.append(Paragraph("Fixed in This Release", styles["H2Custom"]))
        for b in fixed_here:
            story.append(Paragraph(f"<b>{b['bug_id']}</b> &mdash; {b['title']}", styles["BodyCustom"]))
            story.append(Paragraph(b["description"], styles["BodyCustom"]))

    open_here = [b for b in bugs if b["affected_version"] == version and b["status"] in ("Open", "Won't Fix")]
    if open_here:
        story.append(Paragraph("Known Issues", styles["H2Custom"]))
        rows = [[Paragraph(h, styles["CellHeader"]) for h in ["Bug ID", "Severity", "Status", "Description"]]]
        for b in open_here:
            rows.append([
                Paragraph(b["bug_id"], styles["CellText"]),
                Paragraph(b["severity"], styles["CellText"]),
                Paragraph(b["status"], styles["CellText"]),
                Paragraph(b["description"], styles["CellText"]),
            ])
        col_widths = [1.1 * inch, 0.65 * inch, 0.55 * inch, 3.5 * inch]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    story.append(Paragraph("Upgrade Notes", styles["H2Custom"]))
    story.append(Paragraph(copy["upgrade_notes"], styles["BodyCustom"]))

    out_path = f"{DOCS_OUT}/InvoicePilot_Release_Notes_v{version}.pdf"
    doc = SimpleDocTemplate(out_path, pagesize=letter,
                             topMargin=0.9 * inch, bottomMargin=0.8 * inch,
                             leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                             title=f"InvoicePilot Release Notes v{version}")
    doc.build(story)
    print("wrote", out_path)
