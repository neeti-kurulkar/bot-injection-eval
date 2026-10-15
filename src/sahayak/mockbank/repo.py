"""Repository layer: all SQL for the mock core bank lives here (ADR-0003).

Rules this module guarantees:
- The audit log has append and read functions only (and the schema blocks
  UPDATE/DELETE with triggers).
- Money moves only in `execute_approved_transfer`. It refuses any approval
  without status 'approved' and a named human approver. No tool calls it.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from sahayak.mockbank.schema import SCHEMA_SQL, WORLD_TABLES


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def build_template_db(world_dir: Path, db_path: Path) -> dict[str, int]:
    """Build the seeded template DB from the Stage 1 world files. Returns row counts."""
    import csv

    if db_path.exists():
        db_path.unlink()
    conn = _connect(db_path)
    conn.executescript(SCHEMA_SQL)
    counts = {}
    for fname, (table, cols) in WORLD_TABLES.items():
        rows = json.loads((world_dir / fname).read_text(encoding="utf-8"))
        conn.executemany(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [tuple(int(r[c]) if isinstance(r[c], bool) else r[c] for c in cols) for r in rows],
        )
        counts[table] = len(rows)
    with (world_dir / "transactions.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        txns = [tuple(int(r[c]) if c == "amount_paise" else r[c] for c in cols) for r in reader]
    conn.executemany(
        f"INSERT INTO transactions ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", txns)
    counts["transactions"] = len(txns)
    conn.commit()
    conn.close()
    return counts


def copy_db(template: Path, dest: Path) -> Path:
    """Fresh per-scenario copy of the template DB."""
    shutil.copyfile(template, dest)
    return dest


class Repository:
    def __init__(self, conn: sqlite3.Connection, clock: Callable[[], str] = utc_now):
        self.conn = conn
        self.clock = clock

    @classmethod
    def open(cls, path: Path | str, clock: Callable[[], str] = utc_now) -> Repository:
        return cls(_connect(path), clock)

    @classmethod
    def in_memory(cls, clock: Callable[[], str] = utc_now) -> Repository:
        conn = _connect(":memory:")
        conn.executescript(SCHEMA_SQL)
        return cls(conn, clock)

    def close(self) -> None:
        self.conn.close()

    def _one(self, sql: str, *args) -> dict | None:
        row = self.conn.execute(sql, args).fetchone()
        return dict(row) if row else None

    def _all(self, sql: str, *args) -> list[dict]:
        return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def _insert(self, table: str, row: dict) -> int:
        cols = list(row)
        cur = self.conn.execute(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [row[c] for c in cols])
        self.conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------ reads
    def get_customer(self, customer_id: str) -> dict | None:
        return self._one("SELECT * FROM customers WHERE customer_id = ?", customer_id)

    def get_account(self, account_id: str) -> dict | None:
        return self._one("SELECT * FROM accounts WHERE account_id = ?", account_id)

    def get_card(self, card_id: str) -> dict | None:
        return self._one("SELECT * FROM cards WHERE card_id = ?", card_id)

    def get_transaction(self, txn_id: str) -> dict | None:
        return self._one("SELECT * FROM transactions WHERE txn_id = ?", txn_id)

    def get_ticket(self, ticket_id: str) -> dict | None:
        return self._one("SELECT * FROM tickets WHERE ticket_id = ?", ticket_id)

    def accounts_of(self, customer_id: str) -> list[dict]:
        return self._all("SELECT * FROM accounts WHERE customer_id = ? ORDER BY account_id", customer_id)

    def notes_for_customer(self, customer_id: str) -> list[dict]:
        return self._all(
            "SELECT n.* FROM account_notes n JOIN accounts a ON a.account_id = n.account_id "
            "WHERE a.customer_id = ? ORDER BY n.created_at, n.note_id", customer_id)

    def tickets_of(self, customer_id: str) -> list[dict]:
        return self._all("SELECT * FROM tickets WHERE customer_id = ? ORDER BY created_at, ticket_id",
                         customer_id)

    def recent_transactions(self, account_id: str, n: int) -> list[dict]:
        return self._all(
            "SELECT * FROM transactions WHERE account_id = ? ORDER BY ts DESC, txn_id DESC LIMIT ?",
            account_id, n)

    def beneficiary(self, customer_id: str, account_ref: str) -> dict | None:
        return self._one("SELECT * FROM beneficiaries WHERE customer_id = ? AND account_ref = ?",
                         customer_id, account_ref)

    def branch_by_city(self, city: str) -> dict | None:
        return self._one("SELECT * FROM branches WHERE lower(city) = lower(?)", city)

    def branches(self) -> list[dict]:
        return self._all("SELECT * FROM branches ORDER BY branch_id")

    # ----------------------------------------------- owner resolution
    def owner_of(self, kind: str, resource_id: str) -> str | None:
        """Customer who owns an account / card / transaction / ticket, or None if unknown."""
        sql = {
            "account": "SELECT customer_id FROM accounts WHERE account_id = ?",
            "card": "SELECT a.customer_id FROM cards c JOIN accounts a ON a.account_id = c.account_id "
                    "WHERE c.card_id = ?",
            "transaction": "SELECT a.customer_id FROM transactions t JOIN accounts a "
                           "ON a.account_id = t.account_id WHERE t.txn_id = ?",
            "ticket": "SELECT customer_id FROM tickets WHERE ticket_id = ?",
        }[kind]
        row = self.conn.execute(sql, (resource_id,)).fetchone()
        return row[0] if row else None

    # ------------------------------------------------------ T2 writes
    def set_card_status(self, card_id: str, status: str) -> None:
        self.conn.execute("UPDATE cards SET status = ? WHERE card_id = ?", (status, card_id))
        self.conn.commit()

    def insert_dispute(self, session_id: str, txn_id: str, reason: str) -> str:
        seq = self._insert("disputes", {"session_id": session_id, "transaction_id": txn_id,
                                        "reason": reason, "status": "open", "created_at": self.clock()})
        dispute_id = f"DSP-{seq:05d}"
        self.conn.execute("UPDATE disputes SET dispute_id = ? WHERE seq = ?", (dispute_id, seq))
        self.conn.commit()
        return dispute_id

    def update_contact(self, session_id: str, customer_id: str, field: str, value: str) -> None:
        old = self.get_customer(customer_id)[field]
        self._insert("contact_changes", {"session_id": session_id, "customer_id": customer_id,
                                         "field": field, "old_value": old, "new_value": value,
                                         "created_at": self.clock()})
        self.conn.execute(f"UPDATE customers SET {'phone' if field == 'phone' else 'email'} = ? "
                          "WHERE customer_id = ?", (value, customer_id))
        self.conn.commit()

    # ------------------------------------------- T3 queue (no money)
    def insert_approval(self, session_id: str, action: str, args: dict, policy_result: str,
                        status: str) -> str:
        seq = self._insert("approvals", {
            "session_id": session_id, "action": action,
            "args_json": json.dumps(args, sort_keys=True, ensure_ascii=False),
            "policy_result": policy_result, "status": status, "created_at": self.clock()})
        approval_id = f"AP-{seq:05d}"
        self.conn.execute("UPDATE approvals SET approval_id = ? WHERE seq = ?", (approval_id, seq))
        self.conn.commit()
        return approval_id

    def get_approval(self, approval_id: str) -> dict | None:
        return self._one("SELECT * FROM approvals WHERE approval_id = ?", approval_id)

    def list_approvals(self, session_id: str | None = None) -> list[dict]:
        if session_id is None:
            return self._all("SELECT * FROM approvals ORDER BY seq")
        return self._all("SELECT * FROM approvals WHERE session_id = ? ORDER BY seq", session_id)

    def record_approval_decision(self, approval_id: str, approver: str, approve: bool) -> None:
        """Human approver action. Never called by the ToolLayer or the agent."""
        if not approver:
            raise ValueError("a named human approver is required")
        ap = self.get_approval(approval_id)
        if ap is None or ap["status"] != "pending":
            raise ValueError(f"approval {approval_id} is not pending")
        self.conn.execute("UPDATE approvals SET status = ?, approver = ?, decided_at = ? WHERE approval_id = ?",
                          ("approved" if approve else "declined", approver, self.clock(), approval_id))
        self.conn.commit()

    def execute_approved_transfer(self, approval_id: str) -> None:
        """The only function that moves money. Requires a human approval record."""
        ap = self.get_approval(approval_id)
        if ap is None or ap["status"] != "approved" or not ap["approver"]:
            raise PermissionError("T3 action requires an approval with status 'approved' and a named approver")
        if ap["action"] != "propose_transfer":
            raise PermissionError("only transfers are executable in the mock bank")
        args = json.loads(ap["args_json"])
        amount = int(args["amount_paise"])
        src = self.get_account(args["from_account_id"])
        if src is None or src["balance_paise"] < amount:
            raise ValueError("insufficient funds")
        self.conn.execute("UPDATE accounts SET balance_paise = balance_paise - ? WHERE account_id = ?",
                          (amount, args["from_account_id"]))
        if self.get_account(args["to_account_id"]) is not None:
            self.conn.execute("UPDATE accounts SET balance_paise = balance_paise + ? WHERE account_id = ?",
                              (amount, args["to_account_id"]))
        self.conn.commit()

    # ------------------------------------------------------ handoff
    def insert_handoff(self, session_id: str, customer_id: str | None, kind: str, reason: str) -> str:
        seq = self._insert("handoffs", {"session_id": session_id, "customer_id": customer_id,
                                        "kind": kind, "reason": reason, "created_at": self.clock()})
        handoff_id = f"HO-{seq:05d}"
        self.conn.execute("UPDATE handoffs SET handoff_id = ? WHERE seq = ?", (handoff_id, seq))
        self.conn.commit()
        return handoff_id

    def list_handoffs(self, session_id: str | None = None) -> list[dict]:
        if session_id is None:
            return self._all("SELECT * FROM handoffs ORDER BY seq")
        return self._all("SELECT * FROM handoffs WHERE session_id = ? ORDER BY seq", session_id)

    def insert_complaint_ticket(self, customer_id: str, language: str, body: str) -> str:
        n = self.conn.execute("SELECT COUNT(*) FROM tickets WHERE ticket_id LIKE 'TKN%'").fetchone()[0] + 1
        ticket_id = f"TKN{n:05d}"
        self._insert("tickets", {"ticket_id": ticket_id, "customer_id": customer_id, "created_at": self.clock(),
                                 "category": "complaint", "language": language, "subject": "Complaint",
                                 "body": body, "status": "open"})
        return ticket_id

    # --------------------------------------------------------- audit
    def append_audit(self, *, session_id: str, condition: str, tool: str, tier: str, args: dict,
                     allowed: bool, reason: str, result_digest: str,
                     would_deny_in_b: str | None = None) -> int:
        return self._insert("audit_log", {
            "ts": self.clock(), "session_id": session_id, "condition": condition, "tool": tool,
            "tier": tier, "args_json": json.dumps(args, sort_keys=True, ensure_ascii=False),
            "allowed": int(allowed), "reason": reason, "would_deny_in_b": would_deny_in_b,
            "result_digest": result_digest})

    def list_audit(self, session_id: str | None = None) -> list[dict]:
        if session_id is None:
            return self._all("SELECT * FROM audit_log ORDER BY seq")
        return self._all("SELECT * FROM audit_log WHERE session_id = ? ORDER BY seq", session_id)
