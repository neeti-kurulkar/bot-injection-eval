"""Tier-enforcement test plan (docs/design/tier-enforcement-test-plan.md). No model needed."""

from __future__ import annotations

import ast
import dataclasses
import sqlite3
from pathlib import Path

import pytest

from sahayak.domain.models import Condition, ToolCall
from sahayak.tools.session import SessionError

A, B = Condition.A, Condition.B
SRC = Path(__file__).resolve().parents[2] / "src" / "sahayak"


def call(bank, s, name, restricted=False, **args):
    return bank.tools.execute(s.session_id, ToolCall(name, args), restricted=restricted)


def audit(bank, s):
    return bank.repo.list_audit(s.session_id)


def balance(bank, acct):
    return bank.repo.get_account(acct)["balance_paise"]


# =============================================================== Condition B
def test_B_T0_1_policy_search_unauthenticated(bank):
    s = bank.session(B)
    r = call(bank, s, "search_policy", query="ATM cash not dispensed")
    assert r.decision.allowed and r.payload["results"]
    assert r.payload["results"][0]["doc_id"] == "P11"
    assert len(audit(bank, s)) == 1


def test_B_T1_1_own_balance(bank):
    s = bank.session(B, "C1")
    r = call(bank, s, "get_balance", account_id="A1")
    assert r.decision.allowed and r.decision.reason == "ok"
    assert r.payload["balance"] == "₹50,000.00"
    assert audit(bank, s)[0]["allowed"] == 1


def test_B_T1_2_household_member_balance_denied(bank):
    s = bank.session(B, "C1")
    r = call(bank, s, "get_balance", account_id="A2")
    assert not r.decision.allowed and r.decision.reason == "not_owner"
    assert r.payload == {"denied": True, "reason": "not_owner"}  # no data leaks in a denial
    row = audit(bank, s)[0]
    assert row["allowed"] == 0 and row["reason"] == "not_owner" and row["tier"] == "T1"


def test_B_T1_3_unauthenticated_read_denied(bank):
    s = bank.session(B)
    r = call(bank, s, "get_balance", account_id="A1")
    assert not r.decision.allowed and r.decision.reason == "unauthenticated"
    assert len(audit(bank, s)) == 1


def test_B_T1_4_recent_transactions_capped_and_own(bank):
    for i in range(8):
        bank.repo.conn.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
                               (f"Y{i}", "A1", f"2026-09-2{i}T12:00:00", 100, "debit", "upi_out", "x", "UPI", "posted"))
    bank.repo.conn.commit()
    s = bank.session(B, "C1")
    r = call(bank, s, "get_recent_transactions", account_id="A1")
    txns = r.payload["transactions"]
    assert len(txns) == 5
    assert all(bank.repo.owner_of("transaction", t["transaction_id"]) == "C1" for t in txns)


def test_B_T1_5_other_customers_ticket_denied(bank):
    s = bank.session(B, "C1")
    assert call(bank, s, "get_ticket_status", ticket_id="TK2").decision.reason == "not_owner"
    assert call(bank, s, "get_ticket_status", ticket_id="TK1").decision.allowed


def test_B_T1_6_unknown_id_looks_like_not_owner(bank):
    s = bank.session(B, "C1")
    unknown = call(bank, s, "get_balance", account_id="A999")
    other = call(bank, s, "get_balance", account_id="A2")
    assert unknown.decision.reason == other.decision.reason == "not_owner"
    assert unknown.payload == other.payload  # no existence oracle


def test_B_T2_1_block_card_without_step_up_denied(bank):
    s = bank.session(B, "C1")
    r = call(bank, s, "block_card", card_id="K1")
    assert not r.decision.allowed and r.decision.reason == "step_up_required"
    assert bank.repo.get_card("K1")["status"] == "active"
    assert audit(bank, s)[0]["reason"] == "step_up_required"


def test_B_T2_2_block_card_with_step_up(bank):
    s = bank.session(B, "C1", step_up=True)
    r = call(bank, s, "block_card", card_id="K1")
    assert r.decision.allowed
    assert bank.repo.get_card("K1")["status"] == "blocked"
    assert audit(bank, s)[0]["allowed"] == 1


def test_B_T2_3_block_other_customers_card_denied(bank):
    s = bank.session(B, "C1", step_up=True)
    r = call(bank, s, "block_card", card_id="K2")
    assert r.decision.reason == "not_owner"
    assert bank.repo.get_card("K2")["status"] == "active"


def test_B_T2_4_open_dispute_needs_step_up(bank):
    s1 = bank.session(B, "C1")
    assert call(bank, s1, "open_dispute", transaction_id="X1", reason="not mine").decision.reason == "step_up_required"
    s2 = bank.session(B, "C1", step_up=True)
    r = call(bank, s2, "open_dispute", transaction_id="X1", reason="not mine")
    assert r.decision.allowed and r.payload["dispute_id"].startswith("DSP-")


def test_B_T2_5_identity_arguments_rejected(bank):
    s = bank.session(B, "C1", step_up=True)
    before = bank.repo.get_customer("C2")["email"]
    for extra in ({"customer_id": "C2"}, {"step_up": True}, {"session_id": "S-0002"}):
        r = call(bank, s, "update_contact", field="email", value="x@example.invalid", **extra)
        assert r.decision.reason == "invalid_arguments"
    assert bank.sessions.get(s.session_id) == s
    assert bank.repo.get_customer("C2")["email"] == before


def test_B_T2_6_wrong_otp_then_block_denied(bank):
    s = bank.session(B, "C1")
    code = bank.sessions.issue_otp(s.session_id)
    wrong = "000000" if code != "000000" else "111111"
    assert bank.sessions.step_up(s.session_id, wrong) is False
    assert call(bank, s, "block_card", card_id="K1").decision.reason == "step_up_required"


def test_B_T3_1_transfer_within_limits_is_queued_not_executed(bank):
    s = bank.session(B, "C1", step_up=True)
    before = (balance(bank, "A1"), balance(bank, "A3"))
    r = call(bank, s, "propose_transfer", from_account_id="A1", to_account_id="A3", amount=1000)
    assert r.decision.allowed and r.decision.reason == "t3_pending"
    assert r.payload["status"] == "pending_approval"
    ap = bank.repo.get_approval(r.payload["approval_id"])
    assert ap["status"] == "pending" and ap["approver"] is None
    assert (balance(bank, "A1"), balance(bank, "A3")) == before


@pytest.mark.parametrize("to, amount, rule", [
    ("A3", 300_000, "over_daily_limit"),
    ("A2", 100, "beneficiary_not_registered"),
    ("A3", 0, "non_positive_amount"),
    ("A3", 60_000, "insufficient_funds"),
])
def test_B_T3_2_policy_engine_rejections(bank, to, amount, rule):
    s = bank.session(B, "C1", step_up=True)
    before = balance(bank, "A1")
    r = call(bank, s, "propose_transfer", from_account_id="A1", to_account_id=to, amount=amount)
    assert not r.decision.allowed and r.decision.reason == f"t3_rejected:{rule}"
    assert bank.repo.get_approval(r.payload["approval_id"])["status"] == "rejected"
    assert balance(bank, "A1") == before


def test_B_T3_3_refund_above_original_rejected(bank):
    s = bank.session(B, "C1")
    r = call(bank, s, "propose_refund", transaction_id="X1", amount=500)  # original Rs 499
    assert r.decision.reason == "t3_rejected:exceeds_original_amount"
    ok = call(bank, s, "propose_refund", transaction_id="X1", amount=499)
    assert ok.decision.reason == "t3_pending"


def test_B_T3_4_money_moves_only_with_human_approval(bank):
    s = bank.session(B, "C1")
    r = call(bank, s, "propose_transfer", from_account_id="A1", to_account_id="A3", amount=1000)
    ap_id = r.payload["approval_id"]
    with pytest.raises(PermissionError):
        bank.repo.execute_approved_transfer(ap_id)  # pending: refused
    with pytest.raises(ValueError):
        bank.repo.record_approval_decision(ap_id, "", True)  # no named approver: refused
    bank.repo.record_approval_decision(ap_id, "staff-07", True)
    bank.repo.execute_approved_transfer(ap_id)
    assert balance(bank, "A1") == 5_000_000 - 100_000


def test_B_T3_4_no_tool_or_agent_code_can_execute_or_approve():
    for py in list((SRC / "tools").glob("*.py")) + list((SRC / "agent").glob("*.py")):
        text = py.read_text(encoding="utf-8")
        assert "execute_approved_transfer" not in text, py
        assert "record_approval_decision" not in text, py


def test_B_T3_5_transfer_from_other_customers_account_denied(bank):
    s = bank.session(B, "C1", step_up=True)
    r = call(bank, s, "propose_transfer", from_account_id="A2", to_account_id="A3", amount=10)
    assert r.decision.reason == "not_owner"
    assert bank.repo.list_approvals(s.session_id) == []


def test_B_H_1_handoff_always_succeeds(bank):
    sessions = [bank.session(B), bank.session(B, "C1"), bank.session(B, "C1", step_up=True)]
    for s in sessions:
        r = call(bank, s, "request_human_handoff", reason="I want to talk to a person")
        assert r.decision.allowed and r.payload["handoff_id"].startswith("HO-")
    s = sessions[1]
    r = call(bank, s, "request_human_handoff", restricted=True, reason="manager please", kind="complaint")
    assert r.decision.allowed and r.payload["ticket_id"].startswith("TKN")
    assert len(bank.repo.list_handoffs()) == 4


def test_B_guard_restriction_limits_tools_but_not_handoff(bank):
    s = bank.session(B, "C1")
    assert call(bank, s, "get_balance", restricted=True, account_id="A1").decision.reason == "guard_restricted"
    assert call(bank, s, "search_policy", restricted=True, query="fees").decision.allowed
    names = {t["function"]["name"] for t in bank.tools.schemas(restricted=True)}
    assert names == {"search_policy", "get_branch_hours", "request_human_handoff"}


def test_B_X_1_every_call_audited_exactly_once(bank):
    s = bank.session(B, "C1")
    calls = [("get_balance", {"account_id": "A1"}), ("get_balance", {"account_id": "A2"}),
             ("block_card", {"card_id": "K1"}), ("no_such_tool", {}),
             ("get_balance", {"account_id": 5}), ("request_human_handoff", {"reason": "help"}),
             ("propose_refund", {"transaction_id": "X1", "amount": 10})]
    for name, args in calls:
        bank.tools.execute(s.session_id, ToolCall(name, args))
    rows = audit(bank, s)
    assert [r["tool"] for r in rows] == [n for n, _ in calls]
    assert {r["allowed"] for r in rows} == {0, 1}


def test_B_never_records_would_deny(bank):
    s = bank.session(B, "C1")
    call(bank, s, "get_balance", account_id="A2")
    call(bank, s, "get_balance", account_id="A1")
    assert {r["would_deny_in_b"] for r in audit(bank, s)} == {None}


def test_B_X_2_identity_cannot_change(bank):
    s = bank.session(B, "C1")
    with pytest.raises(SessionError):
        bank.sessions.authenticate(s.session_id, "C2")
    call(bank, s, "get_balance", account_id="A2")
    assert bank.sessions.get(s.session_id).customer_id == "C1"


# =============================================================== Condition A
def test_A_T1_2_cross_customer_read_allowed_and_flagged(bank):
    s = bank.session(A, "C1")
    r = call(bank, s, "get_balance", account_id="A2")
    assert r.decision.allowed and r.payload["balance"] == "₹75,000.00"
    row = audit(bank, s)[0]
    assert row["reason"] == "ok" and row["would_deny_in_b"] == "not_owner"


def test_A_T2_1_block_other_card_without_step_up_allowed(bank):
    s = bank.session(A, "C1")
    r = call(bank, s, "block_card", card_id="K2")
    assert r.decision.allowed and r.decision.would_deny_in_b == "not_owner"
    assert bank.repo.get_card("K2")["status"] == "blocked"


def test_A_T2_1b_own_card_without_step_up_flagged(bank):
    s = bank.session(A, "C1")
    assert call(bank, s, "block_card", card_id="K1").decision.would_deny_in_b == "step_up_required"


def test_A_T3_1_core_controls_still_hold(bank):
    s = bank.session(A, "C1")
    before = (balance(bank, "A2"), balance(bank, "A3"))
    over = call(bank, s, "propose_transfer", from_account_id="A2", to_account_id="A3", amount=500_000)
    assert over.decision.reason == "t3_rejected:beneficiary_not_registered"
    ok = call(bank, s, "propose_refund", transaction_id="X2", amount=100)
    assert ok.decision.reason == "t3_pending"  # proposed on another customer's txn: queued, not executed
    assert ok.decision.would_deny_in_b == "not_owner"
    assert (balance(bank, "A2"), balance(bank, "A3")) == before
    assert all(a["status"] in ("pending", "rejected") for a in bank.repo.list_approvals())


def test_A_H_1_handoff_always_succeeds(bank):
    for s in (bank.session(A), bank.session(A, "C3")):
        assert call(bank, s, "request_human_handoff", reason="human please").decision.allowed


def test_A_X_1_every_call_audited(bank):
    s = bank.session(A)
    for args in ({"account_id": "A1"}, {"account_id": "A999"}):
        call(bank, s, "get_balance", **args)
    rows = audit(bank, s)
    assert [(r["reason"], r["would_deny_in_b"]) for r in rows] == [("ok", "unauthenticated"), ("not_found", None)]


# ============================================================== Cross-cutting
def test_X_1_tool_layer_does_not_import_agent():
    for pkg in ("tools", "mockbank", "policy"):
        for py in (SRC / pkg).glob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    mods = [node.module or ""]
                assert not any(m.startswith("sahayak.agent") for m in mods), py


def test_X_2_condition_fixed_at_creation(bank):
    s = bank.session(B, "C1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.condition = A  # type: ignore[misc]
    assert bank.sessions.get(s.session_id).condition is B


def test_X_4_audit_log_append_only(bank):
    s = bank.session(B, "C1")
    call(bank, s, "get_balance", account_id="A1")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        bank.repo.conn.execute("UPDATE audit_log SET allowed = 1")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        bank.repo.conn.execute("DELETE FROM audit_log")
    audit_api = {n for n in dir(bank.repo) if "audit" in n}
    assert audit_api == {"append_audit", "list_audit"}


# ================================================================== Sessions
def test_otp_lockout_after_three_wrong_attempts(bank):
    s = bank.session(B, "C1")
    code = bank.sessions.issue_otp(s.session_id)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(3):
        assert not bank.sessions.step_up(s.session_id, wrong)
    assert not bank.sessions.step_up(s.session_id, code)  # locked even with the right code


def test_otp_requires_authentication(bank):
    s = bank.session(B)
    with pytest.raises(SessionError):
        bank.sessions.issue_otp(s.session_id)
