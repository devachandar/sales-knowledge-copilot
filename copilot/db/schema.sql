-- copilot/db/schema.sql
-- InvoicePilot tables, in their own schema, with real types and foreign keys.

CREATE SCHEMA IF NOT EXISTS ip;

DROP TABLE IF EXISTS ip.support_tickets, ip.usage_logs, ip.sales_records,
                     ip.bugs, ip.customers, ip.product_versions CASCADE;

CREATE TABLE ip.product_versions (
    version       TEXT PRIMARY KEY,
    codename      TEXT NOT NULL,
    release_date  DATE NOT NULL,
    summary       TEXT
);

CREATE TABLE ip.customers (
    customer_id   TEXT PRIMARY KEY,
    company_name  TEXT NOT NULL,
    industry      TEXT,
    country       TEXT,
    account_tier  TEXT NOT NULL CHECK (account_tier IN ('Starter','Professional','Enterprise')),
    signup_date   DATE NOT NULL
);

CREATE TABLE ip.bugs (
    bug_id           TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    affected_version TEXT NOT NULL REFERENCES ip.product_versions,
    fixed_in_version TEXT REFERENCES ip.product_versions,   -- NULL = not fixed
    severity         TEXT NOT NULL,
    status           TEXT NOT NULL,
    reported_date    DATE NOT NULL,
    description      TEXT
);

CREATE TABLE ip.sales_records (
    sale_id             TEXT PRIMARY KEY,
    customer_id         TEXT NOT NULL REFERENCES ip.customers,
    order_date          DATE NOT NULL,
    order_type          TEXT NOT NULL,
    product_version     TEXT NOT NULL REFERENCES ip.product_versions,
    plan                TEXT NOT NULL,
    seats_purchased     INT  NOT NULL,
    unit_price_usd      INT  NOT NULL,
    total_amount_usd    INT  NOT NULL,
    sales_rep           TEXT,
    license_status      TEXT NOT NULL,
    license_expiry_date DATE NOT NULL
);

CREATE TABLE ip.usage_logs (
    customer_id      TEXT NOT NULL REFERENCES ip.customers,
    month            DATE NOT NULL,                  -- first day of the month
    product_version  TEXT NOT NULL REFERENCES ip.product_versions,
    active_seats     INT  NOT NULL,
    seats_licensed   INT  NOT NULL,
    logins           INT  NOT NULL,
    features_used    TEXT[] NOT NULL,
    last_active_date DATE,
    PRIMARY KEY (customer_id, month)
);

CREATE TABLE ip.support_tickets (
    ticket_id        TEXT PRIMARY KEY,
    customer_id      TEXT NOT NULL REFERENCES ip.customers,
    created_date     DATE NOT NULL,
    product_version  TEXT NOT NULL REFERENCES ip.product_versions,
    category         TEXT NOT NULL,
    subject          TEXT,
    description      TEXT,
    linked_bug_id    TEXT REFERENCES ip.bugs,
    status           TEXT NOT NULL
);