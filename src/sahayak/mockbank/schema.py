"""SQLite schema for the mock core bank (ADR-0003). Money is integer paise."""

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    household_id TEXT NOT NULL,
    city TEXT NOT NULL,
    is_metro INTEGER NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    preferred_language TEXT NOT NULL,
    kyc_risk TEXT NOT NULL
);

CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),  -- exactly one owner
    account_type TEXT NOT NULL,
    branch_city TEXT NOT NULL,
    opened_on TEXT NOT NULL,
    opening_balance_paise INTEGER NOT NULL,
    balance_paise INTEGER NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE cards (
    card_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    variant TEXT NOT NULL,
    last4 TEXT NOT NULL,
    expiry TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE transactions (
    txn_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    ts TEXT NOT NULL,
    amount_paise INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('debit', 'credit')),
    txn_type TEXT NOT NULL,
    description TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE INDEX ix_txn_account_ts ON transactions(account_id, ts);

CREATE TABLE beneficiaries (
    beneficiary_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    nickname TEXT NOT NULL,
    account_ref TEXT NOT NULL,
    bank TEXT NOT NULL,
    added_on TEXT NOT NULL
);

CREATE TABLE tickets (
    ticket_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    created_at TEXT NOT NULL,
    category TEXT NOT NULL,
    language TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE account_notes (
    note_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    author TEXT NOT NULL,
    created_at TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE TABLE branches (
    branch_id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    is_metro INTEGER NOT NULL,
    address TEXT NOT NULL
);

-- Runtime tables, written by the ToolLayer during a scenario.
CREATE TABLE approvals (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_id TEXT UNIQUE,
    session_id TEXT NOT NULL,
    action TEXT NOT NULL,
    args_json TEXT NOT NULL,
    policy_result TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'rejected', 'approved', 'declined')),
    approver TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE handoffs (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    handoff_id TEXT UNIQUE,
    session_id TEXT NOT NULL,
    customer_id TEXT,
    kind TEXT NOT NULL CHECK (kind IN ('handoff', 'complaint')),
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE disputes (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    dispute_id TEXT UNIQUE,
    session_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL REFERENCES transactions(txn_id),
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE contact_changes (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    field TEXT NOT NULL CHECK (field IN ('phone', 'email')),
    old_value TEXT NOT NULL,
    new_value TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE audit_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    session_id TEXT NOT NULL,
    condition TEXT NOT NULL,
    tool TEXT NOT NULL,
    tier TEXT NOT NULL,
    args_json TEXT NOT NULL,
    allowed INTEGER NOT NULL,
    reason TEXT NOT NULL,
    would_deny_in_b TEXT,  -- Condition A only: the check B would have failed (NULL if none)
    result_digest TEXT NOT NULL
);

-- The audit log is append-only at the storage level, not only by convention.
CREATE TRIGGER audit_log_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER audit_log_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
"""

WORLD_TABLES = {
    # file name -> (table, columns in insert order)
    "customers.json": ("customers", ("customer_id", "display_name", "household_id", "city", "is_metro",
                                     "phone", "email", "preferred_language", "kyc_risk")),
    "accounts.json": ("accounts", ("account_id", "customer_id", "account_type", "branch_city", "opened_on",
                                   "opening_balance_paise", "balance_paise", "status")),
    "cards.json": ("cards", ("card_id", "account_id", "variant", "last4", "expiry", "status")),
    "beneficiaries.json": ("beneficiaries", ("beneficiary_id", "customer_id", "nickname", "account_ref",
                                             "bank", "added_on")),
    "tickets.json": ("tickets", ("ticket_id", "customer_id", "created_at", "category", "language",
                                 "subject", "body", "status")),
    "account_notes.json": ("account_notes", ("note_id", "account_id", "author", "created_at", "body")),
    "branches.json": ("branches", ("branch_id", "city", "is_metro", "address")),
}
