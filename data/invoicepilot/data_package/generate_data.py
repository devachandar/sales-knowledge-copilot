"""
Generates a small, self-consistent POC dataset for a fictional SaaS product
called InvoicePilot (a Zoho-Books-style invoicing/accounting SaaS).

Produces:
  - customers.csv
  - product_versions.csv
  - sales_records.csv
  - usage_logs.csv
  - bugs.csv
  - support_tickets.csv

All tables share customer_id / version / bug_id keys so a RAG agent can
join sales + usage + docs + bug data to answer multi-hop questions like:
  "Was Oracle using the platform legitimately this month, were they sold
   version 2.3.1, and was there a known bug in that version?"
"""
import csv
import random
from datetime import date, datetime, timedelta

random.seed(42)

OUT = "/home/claude/data"
import os
os.makedirs(OUT, exist_ok=True)

TODAY = date(2026, 9, 15)

# ---------------------------------------------------------------------------
# 1. Product versions
# ---------------------------------------------------------------------------
VERSIONS = [
    {
        "version": "2.0.0", "codename": "Nova",
        "release_date": "2025-06-10",
        "summary": "Major redesign of the core app with native multi-currency support.",
    },
    {
        "version": "2.1.0", "codename": "Solstice",
        "release_date": "2025-09-16",
        "summary": "Automated recurring invoices and receipt-scanning for expenses.",
    },
    {
        "version": "2.2.0", "codename": "Meridian",
        "release_date": "2026-01-20",
        "summary": "Redesigned client portal, bulk invoice actions, and API v2.",
    },
    {
        "version": "2.3.0", "codename": "Aurora",
        "release_date": "2026-05-11",
        "summary": "Automatic bank-reconciliation matching and a custom report builder.",
    },
    {
        "version": "2.3.1", "codename": "Aurora Patch 1",
        "release_date": "2026-08-14",
        "summary": "Patch release fixing recurring-invoice timezone bugs and PDF export issues.",
    },
]

with open(f"{OUT}/product_versions.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["version", "codename", "release_date", "summary"])
    w.writeheader()
    for v in VERSIONS:
        w.writerow(v)

VERSION_ORDER = [v["version"] for v in VERSIONS]
VERSION_DATES = {v["version"]: datetime.strptime(v["release_date"], "%Y-%m-%d").date() for v in VERSIONS}

# ---------------------------------------------------------------------------
# 2. Bugs (tagged by affected version)
# ---------------------------------------------------------------------------
BUGS = [
    {"bug_id": "BUG-2000-01", "title": "Currency rounding error on invoice totals",
     "affected_version": "2.0.0", "fixed_in_version": "2.1.0", "severity": "High",
     "status": "Fixed", "reported_date": "2025-06-22",
     "description": "Invoices in JPY and other zero-decimal currencies rounded totals incorrectly, overcharging customers by up to 1 unit per line item."},
    {"bug_id": "BUG-2000-02", "title": "Dashboard fails to load for accounts with 500+ contacts",
     "affected_version": "2.0.0", "fixed_in_version": "2.0.0", "severity": "Medium",
     "status": "Fixed", "reported_date": "2025-06-28",
     "description": "Large accounts saw a blank dashboard due to an unpaginated contacts query timing out."},
    {"bug_id": "BUG-2100-01", "title": "Receipt OCR misreads handwritten totals",
     "affected_version": "2.1.0", "fixed_in_version": None, "severity": "Low",
     "status": "Won't Fix", "reported_date": "2025-09-30",
     "description": "OCR accuracy on handwritten receipts is below 40%; typed/printed receipts are unaffected. Documented as a known limitation."},
    {"bug_id": "BUG-2100-02", "title": "Recurring invoices skip a cycle across DST changes",
     "affected_version": "2.1.0", "fixed_in_version": "2.3.1", "severity": "High",
     "status": "Fixed", "reported_date": "2025-10-05",
     "description": "Recurring invoice schedules calculated in local time skipped a billing cycle when daylight-saving time shifted, causing missed invoices for some customers."},
    {"bug_id": "BUG-2200-01", "title": "Client portal login loop on Safari",
     "affected_version": "2.2.0", "fixed_in_version": "2.2.0", "severity": "Medium",
     "status": "Fixed", "reported_date": "2026-01-25",
     "description": "Safari users were redirected back to the login page after successful authentication due to a cookie SameSite misconfiguration."},
    {"bug_id": "BUG-2200-02", "title": "API v2 rate limit headers missing",
     "affected_version": "2.2.0", "fixed_in_version": "2.3.0", "severity": "Low",
     "status": "Fixed", "reported_date": "2026-02-02",
     "description": "API v2 responses did not include X-RateLimit-* headers, making it hard for integrators to back off proactively."},
    {"bug_id": "BUG-2300-01", "title": "Custom report builder times out on 3+ year date ranges",
     "affected_version": "2.3.0", "fixed_in_version": None, "severity": "Medium",
     "status": "Open", "reported_date": "2026-05-20",
     "description": "Reports spanning more than 3 years of transactions time out instead of paginating results."},
    {"bug_id": "BUG-2310-01", "title": "Bank reconciliation auto-match fails for multi-currency accounts",
     "affected_version": "2.3.1", "fixed_in_version": None, "severity": "Critical",
     "status": "Open", "reported_date": "2026-08-25",
     "description": "Auto-match in bank reconciliation does not convert foreign-currency transactions before comparing amounts, so multi-currency accounts see most transactions left unmatched."},
    {"bug_id": "BUG-2310-02", "title": "PDF export drops the second page of long invoices",
     "affected_version": "2.3.1", "fixed_in_version": None, "severity": "High",
     "status": "Open", "reported_date": "2026-08-29",
     "description": "Invoices with more than 25 line items export as a single-page PDF, silently dropping remaining line items."},
    {"bug_id": "BUG-2310-03", "title": "Minor: report builder date picker shows wrong first day of week",
     "affected_version": "2.3.1", "fixed_in_version": None, "severity": "Low",
     "status": "Open", "reported_date": "2026-09-02",
     "description": "The date-range picker in the custom report builder always starts weeks on Sunday, ignoring the organization's locale setting."},
]

with open(f"{OUT}/bugs.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["bug_id", "title", "affected_version", "fixed_in_version",
                                      "severity", "status", "reported_date", "description"])
    w.writeheader()
    for b in BUGS:
        w.writerow(b)

BUGS_BY_VERSION = {}
for b in BUGS:
    BUGS_BY_VERSION.setdefault(b["affected_version"], []).append(b)

# ---------------------------------------------------------------------------
# 3. Customers
# ---------------------------------------------------------------------------
COMPANIES = [
    ("Oracle", "Enterprise Software", "United States"),
    ("Acme Corporation", "Manufacturing", "United States"),
    ("Globex Corporation", "Conglomerate", "United States"),
    ("Initech", "IT Services", "United States"),
    ("Umbrella Corp", "Pharmaceuticals", "Germany"),
    ("Stark Industries", "Defense & Energy", "United States"),
    ("Wayne Enterprises", "Conglomerate", "United States"),
    ("Soylent Corp", "Food & Beverage", "United States"),
    ("Hooli", "Technology", "United States"),
    ("Massive Dynamic", "R&D", "United States"),
    ("Cyberdyne Systems", "Robotics", "United States"),
    ("Wonka Industries", "Food & Beverage", "United Kingdom"),
    ("Gringotts Financial", "Financial Services", "United Kingdom"),
    ("Vandelay Industries", "Import/Export", "United States"),
    ("Prestige Worldwide", "Media", "United States"),
    ("Dunder Mifflin", "Paper & Office Supplies", "United States"),
    ("Sterling Cooper", "Advertising", "United States"),
    ("Bluth Company", "Real Estate", "United States"),
    ("Monsters Inc", "Energy", "United States"),
    ("Weyland-Yutani", "Aerospace", "United States"),
    ("Pied Piper", "Technology", "United States"),
    ("Los Pollos Hermanos", "Food & Beverage", "United States"),
    ("Nakatomi Trading", "Real Estate", "Japan"),
    ("Oceanic Airlines", "Aviation", "Australia"),
    ("Tyrell Corporation", "Biotech", "United States"),
    ("Aperture Science", "R&D", "United States"),
    ("Genco Pura Olive Oil", "Food & Beverage", "Italy"),
    ("Springfield Nuclear", "Energy", "United States"),
    ("Buy N Large", "Retail", "United States"),
    ("Wonderland Media", "Media", "Canada"),
]

TIERS = ["Starter", "Professional", "Enterprise"]
TIER_WEIGHTS = [0.3, 0.4, 0.3]

customers = []
for i, (name, industry, country) in enumerate(COMPANIES, start=1):
    cust_id = f"CUST-{i:04d}"
    signup_date = TODAY - timedelta(days=random.randint(200, 900))
    tier = random.choices(TIERS, weights=TIER_WEIGHTS, k=1)[0]
    customers.append({
        "customer_id": cust_id,
        "company_name": name,
        "industry": industry,
        "country": country,
        "account_tier": tier,
        "signup_date": signup_date.isoformat(),
    })

# Force Oracle's profile for the demo scenario: long-standing Enterprise customer
oracle = customers[0]
oracle["account_tier"] = "Enterprise"
oracle["signup_date"] = date(2025, 5, 2).isoformat()

with open(f"{OUT}/customers.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["customer_id", "company_name", "industry", "country",
                                      "account_tier", "signup_date"])
    w.writeheader()
    for c in customers:
        w.writerow(c)

# ---------------------------------------------------------------------------
# 4. Sales / license records
# ---------------------------------------------------------------------------
SALES_REPS = ["Priya Nair", "Daniel Cho", "Marcus Webb", "Elena Vasquez", "Sam Okafor", "Jordan Blake"]
PLAN_SEAT_PRICE = {"Starter": 12, "Professional": 25, "Enterprise": 40}
ORDER_TYPES = ["New", "Renewal", "Upgrade", "Add Seats"]

sales_records = []
sale_counter = 1

def add_sale(customer, order_date, version, order_type, seats, expiry_days=365, status="Active"):
    global sale_counter
    plan = customer["account_tier"]
    price = PLAN_SEAT_PRICE[plan]
    total = price * seats
    expiry = order_date + timedelta(days=expiry_days)
    sales_records.append({
        "sale_id": f"SALE-{sale_counter:05d}",
        "customer_id": customer["customer_id"],
        "order_date": order_date.isoformat(),
        "order_type": order_type,
        "product_version": version,
        "plan": plan,
        "seats_purchased": seats,
        "unit_price_usd": price,
        "total_amount_usd": total,
        "sales_rep": random.choice(SALES_REPS),
        "license_status": status,
        "license_expiry_date": expiry.isoformat(),
    })
    sale_counter += 1

for c in customers:
    signup = date.fromisoformat(c["signup_date"])
    # pick the version that existed at signup time (or the first version)
    available = [v for v in VERSIONS if VERSION_DATES[v["version"]] <= signup]
    start_version = (available[-1] if available else VERSIONS[0])["version"]
    seats = random.randint(5, 60) if c["account_tier"] != "Enterprise" else random.randint(50, 300)

    # initial purchase
    add_sale(c, signup, start_version, "New", seats)

    # simulate renewals/upgrades roughly every ~4 months up to today
    cursor = signup
    current_version_idx = VERSION_ORDER.index(start_version)
    while True:
        cursor = cursor + timedelta(days=random.randint(45, 85))
        if cursor > TODAY:
            break
        # decide event type
        roll = random.random()
        # possibly move to a newer version that existed by 'cursor'
        available_now = [v["version"] for v in VERSIONS if VERSION_DATES[v["version"]] <= cursor]
        newest_available_idx = VERSION_ORDER.index(available_now[-1]) if available_now else current_version_idx
        if newest_available_idx > current_version_idx and roll < 0.55:
            current_version_idx = newest_available_idx
            add_sale(c, cursor, VERSION_ORDER[current_version_idx], "Upgrade", seats)
        elif roll < 0.8:
            seats_delta = random.choice([0, 0, 5, 10, -5])
            seats = max(3, seats + seats_delta)
            order_type = "Renewal" if seats_delta == 0 else "Add Seats"
            add_sale(c, cursor, VERSION_ORDER[current_version_idx], order_type, seats)
        # else: no event this cycle

# --- Force the Oracle demo scenario -----------------------------------------
# Oracle: signed up on 2.0.0, steadily upgraded, most recent order moved them
# onto 2.3.1 (the version with the open critical bank-reconciliation bug),
# on an active Enterprise license.
sales_records = [s for s in sales_records if s["customer_id"] != "CUST-0001"]
oracle_events = [
    (date(2025, 5, 2), "2.0.0", "New", 220),
    (date(2025, 9, 20), "2.1.0", "Upgrade", 220),
    (date(2026, 1, 28), "2.2.0", "Upgrade", 250),
    (date(2026, 5, 18), "2.3.0", "Upgrade", 250),
    (date(2026, 8, 20), "2.3.1", "Upgrade", 260),
]
for order_date, version, order_type, seats in oracle_events:
    add_sale(oracle, order_date, version, order_type, seats, expiry_days=365, status="Active")

with open(f"{OUT}/sales_records.csv", "w", newline="") as f:
    fields = ["sale_id", "customer_id", "order_date", "order_type", "product_version", "plan",
              "seats_purchased", "unit_price_usd", "total_amount_usd", "sales_rep",
              "license_status", "license_expiry_date"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for s in sorted(sales_records, key=lambda r: r["order_date"]):
        w.writerow(s)

print(f"Total sales records: {len(sales_records)}")

# ---------------------------------------------------------------------------
# 5. Usage / telemetry logs (last 6 months)
# ---------------------------------------------------------------------------
MONTHS = ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
FEATURES = ["invoicing", "expenses", "estimates", "recurring_invoices", "bank_reconciliation",
            "reports", "client_portal", "api"]

usage_rows = []

def current_seat_count(customer_id, as_of_month):
    # find latest sale on/before the end of as_of_month
    relevant = [s for s in sales_records if s["customer_id"] == customer_id
                and s["order_date"][:7] <= as_of_month]
    if not relevant:
        return None
    relevant.sort(key=lambda r: r["order_date"])
    return relevant[-1]["seats_purchased"], relevant[-1]["product_version"], relevant[-1]["license_status"]

for c in customers:
    for month in MONTHS:
        info = current_seat_count(c["customer_id"], month)
        if info is None:
            continue
        seats_licensed, version, status = info
        if status != "Active":
            active_seats = 0
            logins = 0
        else:
            utilization = random.uniform(0.55, 0.95)
            active_seats = max(1, int(seats_licensed * utilization))
            logins = active_seats * random.randint(8, 30)
        n_features = random.randint(2, len(FEATURES))
        features_used = random.sample(FEATURES, n_features) if active_seats else []
        usage_rows.append({
            "customer_id": c["customer_id"],
            "month": month,
            "product_version": version,
            "active_seats": active_seats,
            "seats_licensed": seats_licensed,
            "logins": logins,
            "features_used": ";".join(features_used),
            "last_active_date": (datetime.strptime(month, "%Y-%m") +
                                  timedelta(days=random.randint(20, 27))).date().isoformat() if active_seats else "",
        })

# Force Oracle's last 3 months (Jul, Aug, Sep 2026) to show clear, healthy,
# active usage on 2.3.1 -- i.e. legitimately using the platform this month.
for row in usage_rows:
    if row["customer_id"] == "CUST-0001" and row["month"] in ("2026-07", "2026-08", "2026-09"):
        row["active_seats"] = random.randint(230, 255)
        row["seats_licensed"] = 260
        row["logins"] = row["active_seats"] * random.randint(18, 26)
        row["features_used"] = "invoicing;bank_reconciliation;reports;client_portal;recurring_invoices"
        row["product_version"] = "2.3.1" if row["month"] >= "2026-08" else "2.3.0"
        row["last_active_date"] = "2026-09-14" if row["month"] == "2026-09" else row["last_active_date"]

with open(f"{OUT}/usage_logs.csv", "w", newline="") as f:
    fields = ["customer_id", "month", "product_version", "active_seats", "seats_licensed",
              "logins", "features_used", "last_active_date"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in usage_rows:
        w.writerow(r)

print(f"Total usage rows: {len(usage_rows)}")

# ---------------------------------------------------------------------------
# 6. Support tickets (links customers -> versions -> bugs)
# ---------------------------------------------------------------------------
TICKET_CATEGORIES = ["Bug", "Question", "Feature Request", "Billing"]
NON_BUG_SUBJECTS = [
    "How do I add a new tax rate?",
    "Can we get a custom invoice template?",
    "Requesting an increase in API rate limits",
    "Question about seat-based billing for Add Seats",
    "How to export customer statements in bulk?",
    "Asking about SSO/SAML support for Enterprise plan",
]

tickets = []
ticket_counter = 1

def add_ticket(customer, ticket_date, version, category, subject, description, bug_id=None):
    global ticket_counter
    tickets.append({
        "ticket_id": f"TCKT-{ticket_counter:05d}",
        "customer_id": customer["customer_id"],
        "created_date": ticket_date.isoformat(),
        "product_version": version,
        "category": category,
        "subject": subject,
        "description": description,
        "linked_bug_id": bug_id or "",
        "status": "Resolved" if bug_id and next((b for b in BUGS if b["bug_id"] == bug_id), {}).get("status") == "Fixed" else "Open",
    })
    ticket_counter += 1

# General scattered tickets across customers/time
for c in customers:
    n_tickets = random.randint(0, 3)
    for _ in range(n_tickets):
        ticket_date = TODAY - timedelta(days=random.randint(1, 300))
        if ticket_date < date.fromisoformat(c["signup_date"]):
            continue
        as_of_month = ticket_date.strftime("%Y-%m")
        info = current_seat_count(c["customer_id"], as_of_month)
        if info is None:
            continue
        version = info[1]
        if random.random() < 0.5 and version in BUGS_BY_VERSION:
            bug = random.choice(BUGS_BY_VERSION[version])
            add_ticket(c, ticket_date, version, "Bug", bug["title"], bug["description"], bug["bug_id"])
        else:
            add_ticket(c, ticket_date, version, random.choice(["Question", "Feature Request", "Billing"]),
                       random.choice(NON_BUG_SUBJECTS),
                       "Customer reached out via the support portal with a general request.")

# Force the Oracle demo ticket: they hit the known critical bank-reconciliation
# bug in 2.3.1 last week.
add_ticket(
    oracle, TODAY - timedelta(days=6), "2.3.1", "Bug",
    "Bank reconciliation not matching multi-currency transactions",
    "Our EMEA team reports that since upgrading to 2.3.1, almost none of our "
    "EUR and GBP bank transactions are being auto-matched during reconciliation. "
    "USD transactions match fine.",
    bug_id="BUG-2310-01",
)

with open(f"{OUT}/support_tickets.csv", "w", newline="") as f:
    fields = ["ticket_id", "customer_id", "created_date", "product_version", "category",
              "subject", "description", "linked_bug_id", "status"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for t in sorted(tickets, key=lambda r: r["created_date"]):
        w.writerow(t)

print(f"Total tickets: {len(tickets)}")
print("Done generating CSVs.")
