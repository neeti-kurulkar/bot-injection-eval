"""Shared fixtures. The mini bank mirrors the tier-enforcement test plan:
C1 and C2 share household H1, C3 is unrelated. C1 owns A1 (card K1, txn X1,
ticket TK1); C2 owns A2 (card K2, txn X2, ticket TK2); C3 owns A3. C1 has A3
registered as a beneficiary.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import pytest

from sahayak.domain.models import Condition, Session
from sahayak.generate.policy_corpus import DOCS, render_doc
from sahayak.mockbank.repo import Repository
from sahayak.policy.store import PolicyStore
from sahayak.tools.layer import ToolLayer
from sahayak.tools.session import SessionManager

_POLICIES = None


def corpus_store() -> PolicyStore:
    global _POLICIES
    if _POLICIES is None:
        _POLICIES = PolicyStore.from_texts([render_doc(d)[0] for d in DOCS])
    return _POLICIES


def counter_clock():
    n = itertools.count(1)
    return lambda: f"2026-10-01T10:00:{next(n):02d}.000000Z"


def seed_mini_bank(repo: Repository) -> None:
    rows = {
        "customers": [
            ("C1", "Asha Namuna", "H1", "Mumbai", 1, "+91-00000-00001", "asha@example.invalid", "en", "low"),
            ("C2", "Ravi Namuna", "H1", "Mumbai", 1, "+91-00000-00002", "ravi@example.invalid", "hi-Deva", "low"),
            ("C3", "Uma Fictiva", "H2", "Pune", 0, "+91-00000-00003", "uma@example.invalid", "hinglish", "low"),
        ],
        "accounts": [
            ("A1", "C1", "savings", "Mumbai", "2020-01-01", 5_000_000, 5_000_000, "active"),
            ("A2", "C2", "savings", "Mumbai", "2020-01-01", 7_500_000, 7_500_000, "active"),
            ("A3", "C3", "savings", "Pune", "2020-01-01", 1_000_000, 1_000_000, "active"),
        ],
        "cards": [
            ("K1", "A1", "classic", "1111", "2029-01", "active"),
            ("K2", "A2", "platinum", "2222", "2029-01", "active"),
        ],
        "transactions": [
            ("X1", "A1", "2026-09-20T10:00:00", 49_900, "debit", "card_pos", "Card payment at Demo Supermart", "POS", "posted"),
            ("X2", "A2", "2026-09-21T10:00:00", 120_000, "debit", "upi_out", "UPI to Sample Pharmacy", "UPI", "posted"),
        ],
        "beneficiaries": [("BEN1", "C1", "Friend", "A3", "Sahayak Bank", "2025-01-01")],
        "tickets": [
            ("TK1", "C1", "2026-09-01T10:00:00", "fee_query", "en", "Fee", "Why was I charged?", "open"),
            ("TK2", "C2", "2026-09-02T10:00:00", "fee_query", "hi-Deva", "Fee", "शुल्क क्यों कटा?", "open"),
        ],
        "branches": [("BR01", "Mumbai", 1, "1 Example Road, Mumbai")],
    }
    for table, data in rows.items():
        n = len(data[0])
        repo.conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * n)})", data)
    repo.conn.commit()


@dataclass
class Bank:
    repo: Repository
    sessions: SessionManager
    tools: ToolLayer

    def session(self, condition: Condition, customer: str | None = None, step_up: bool = False) -> Session:
        s = self.sessions.create(condition)
        if customer:
            self.sessions.authenticate(s.session_id, customer)
            if step_up:
                assert self.sessions.step_up(s.session_id, self.sessions.issue_otp(s.session_id))
        return self.sessions.get(s.session_id)


@pytest.fixture
def bank() -> Bank:
    repo = Repository.in_memory(clock=counter_clock())
    seed_mini_bank(repo)
    sessions = SessionManager(repo, seed=7)
    return Bank(repo, sessions, ToolLayer(repo, sessions, corpus_store()))
