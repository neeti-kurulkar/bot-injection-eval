"""Mock bank + ToolLayer end to end on the real Stage 1 world. No model needed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sahayak.config import load_settings
from sahayak.domain.models import Condition, ToolCall
from sahayak.mockbank.repo import Repository, build_template_db, copy_db
from sahayak.policy.store import PolicyStore
from sahayak.tools.layer import ToolLayer
from sahayak.tools.session import SessionManager

WORLD = load_settings().world_dir


@pytest.fixture(scope="module")
def template(tmp_path_factory) -> Path:
    if not (WORLD / "MANIFEST.sha256").exists():
        pytest.skip("world not generated; run scripts/stage1.ps1")
    db = tmp_path_factory.mktemp("tpl") / "sahayak.db"
    build_template_db(WORLD, db)
    return db


@pytest.fixture(scope="module")
def policies() -> PolicyStore:
    return PolicyStore.from_dir(WORLD / "policies")


@pytest.fixture(scope="module")
def household_pair(template) -> tuple[str, str, str, str]:
    """Two customers in one household, with one account each: (c1, a1, c2, a2)."""
    repo = Repository.open(template)
    row = repo.conn.execute(
        "SELECT x.customer_id, y.customer_id FROM customers x JOIN customers y "
        "ON x.household_id = y.household_id AND x.customer_id < y.customer_id ORDER BY x.customer_id LIMIT 1"
    ).fetchone()
    c1, c2 = row
    a1, a2 = repo.accounts_of(c1)[0]["account_id"], repo.accounts_of(c2)[0]["account_id"]
    repo.close()
    return c1, a1, c2, a2


def open_scenario(template: Path, tmp_path: Path, policies: PolicyStore, name: str):
    repo = Repository.open(copy_db(template, tmp_path / f"{name}.db"))
    sessions = SessionManager(repo, seed=1)
    return repo, sessions, ToolLayer(repo, sessions, policies)


def test_template_counts_match_world(template):
    meta = json.loads((WORLD / "world_meta.json").read_text(encoding="utf-8"))["counts"]
    repo = Repository.open(template)
    q = lambda t: repo.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: E731
    assert q("customers") == meta["customers"]
    assert q("accounts") == meta["accounts"]
    assert q("transactions") == meta["transactions"]
    assert q("cards") == meta["cards"]
    assert q("audit_log") == 0 and q("approvals") == 0
    repo.close()


@pytest.mark.parametrize("condition, expect_leak", [(Condition.A, True), (Condition.B, False)])
def test_household_cross_read_by_condition(template, tmp_path, policies, household_pair, condition, expect_leak):
    c1, a1, c2, a2 = household_pair
    repo, sessions, tools = open_scenario(template, tmp_path, policies, condition.value)
    s = sessions.create(condition)
    sessions.authenticate(s.session_id, c1)
    own = tools.execute(s.session_id, ToolCall("get_balance", {"account_id": a1}))
    other = tools.execute(s.session_id, ToolCall("get_balance", {"account_id": a2}))
    assert own.decision.allowed
    assert other.decision.allowed is expect_leak
    rows = repo.list_audit(s.session_id)
    assert len(rows) == 2 and rows[1]["condition"] == condition.value
    assert rows[1]["would_deny_in_b"] == ("not_owner" if condition is Condition.A else None)
    repo.close()


def test_full_flow_condition_B(template, tmp_path, policies, household_pair):
    c1, a1, _, _ = household_pair
    repo, sessions, tools = open_scenario(template, tmp_path, policies, "flow")
    s = sessions.create(Condition.B)
    sessions.authenticate(s.session_id, c1)
    txn = repo.recent_transactions(a1, 1)[0]["txn_id"]
    assert tools.execute(s.session_id, ToolCall("open_dispute", {"transaction_id": txn, "reason": "x"})
                         ).decision.reason == "step_up_required"
    assert sessions.step_up(s.session_id, sessions.issue_otp(s.session_id))
    assert tools.execute(s.session_id, ToolCall("open_dispute", {"transaction_id": txn, "reason": "x"})
                         ).decision.allowed
    before = repo.get_account(a1)["balance_paise"]
    r = tools.execute(s.session_id, ToolCall("propose_refund", {"transaction_id": txn, "amount": 1}))
    assert r.decision.reason in ("t3_pending", "t3_rejected:not_a_posted_debit")
    assert repo.get_account(a1)["balance_paise"] == before
    h = tools.execute(s.session_id, ToolCall("request_human_handoff", {"reason": "talk to a person"}))
    assert h.decision.allowed and len(repo.list_handoffs(s.session_id)) == 1
    assert len(repo.list_audit(s.session_id)) == 4
    repo.close()


def test_X_3_scenario_copies_are_isolated(template, tmp_path, policies):
    repo1, sessions1, tools1 = open_scenario(template, tmp_path, policies, "one")
    card = repo1.conn.execute("SELECT card_id FROM cards WHERE status = 'active' LIMIT 1").fetchone()[0]
    repo1.set_card_status(card, "blocked")
    repo1.append_audit(session_id="S-x", condition="A", tool="block_card", tier="T2", args={},
                       allowed=True, reason="ok", result_digest="-")
    repo1.close()
    repo2, _, _ = open_scenario(template, tmp_path, policies, "two")
    assert repo2.get_card(card)["status"] == "active"
    assert repo2.list_audit() == []
    repo2.close()
