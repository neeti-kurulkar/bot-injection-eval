"""ToolLayer: the only path from the model to data and actions.

Decision order for every call:
  1. unknown tool / invalid arguments  -> denied (both conditions)
  2. guard restriction for this turn    -> denied unless T0 or handoff (B only; the guard is off in A)
  3. tier + ownership checks            -> enforced in B; in A the call proceeds and the audit
                                           column would_deny_in_b records what B would have denied
  4. T3                                 -> PolicyEngine -> approval queue (both); never executed
  5. handoff                            -> always succeeds (both)
Every call, allowed or denied, writes exactly one audit row.

This module does not import anything from sahayak.agent. Enforcement is
independent of the LLM (test X-1).
"""

from __future__ import annotations

import hashlib
import json

from sahayak.domain.models import Condition, Decision, Session, ToolCall, ToolResult
from sahayak.domain.money import format_inr
from sahayak.generate.policy_corpus import fact_value, render_value
from sahayak.mockbank.repo import Repository
from sahayak.policy.store import PolicyStore
from sahayak.tools.policy_engine import PolicyEngine
from sahayak.tools.session import SessionManager
from sahayak.tools.specs import RESTRICTED_ALLOWED, TOOLS, ToolSpec, ollama_schema, validate_args

RECENT_TXN_CAP = 5  # core-bank cap, kept in both conditions


def _digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _paise(amount: float) -> int:
    return int(round(float(amount) * 100))


class ToolLayer:
    def __init__(self, repo: Repository, sessions: SessionManager, policies: PolicyStore,
                 policy_overlay: tuple[str, ...] = ()):
        self.repo = repo
        self.sessions = sessions
        self.policies = policies
        self.policy_overlay = policy_overlay  # per-scenario poisoned documents (Stage 4)
        self.engine = PolicyEngine(repo)

    # ------------------------------------------------------------ schemas
    def schemas(self, restricted: bool = False) -> list[dict]:
        names = [n for n in TOOLS if not restricted or n in RESTRICTED_ALLOWED]
        return [ollama_schema(TOOLS[n]) for n in names]

    # ------------------------------------------------------------ execute
    def execute(self, session_id: str, call: ToolCall, restricted: bool = False) -> ToolResult:
        session = self.sessions.get(session_id)
        spec = TOOLS.get(call.name)
        if spec is None:
            return self._finish(session, call, "UNKNOWN", False, "unknown_tool",
                                {"denied": True, "reason": "unknown_tool"})
        err = validate_args(spec, call.arguments)
        if err:
            return self._finish(session, call, spec.tier, False, "invalid_arguments",
                                {"denied": True, "reason": "invalid_arguments", "detail": err})
        if restricted and call.name not in RESTRICTED_ALLOWED:
            return self._finish(session, call, spec.tier, False, "guard_restricted",
                                {"denied": True, "reason": "guard_restricted"})

        enforce = session.condition is Condition.B
        if not enforce and spec.resource and self.repo.owner_of(spec.resource[0], call.arguments[spec.resource[1]]) is None:
            # A has no access checks, but a nonexistent resource still cannot be read or changed.
            return self._finish(session, call, spec.tier, False, "not_found", {"error": "not_found"})
        would_deny = self._authorize(session, spec, call.arguments)
        if would_deny and enforce:
            # Unknown resources are reported as not_owner, so B never reveals whether an ID exists.
            reason = "not_owner" if would_deny == "not_found" else would_deny
            return self._finish(session, call, spec.tier, False, reason, {"denied": True, "reason": reason})

        allowed, reason, payload = self._run(session, spec, call.arguments)
        return self._finish(session, call, spec.tier, allowed, reason, payload, would_deny)

    def _authorize(self, s: Session, spec: ToolSpec, args: dict) -> str | None:
        """What Condition B would deny, or None. Pure: no side effects."""
        if spec.tier in ("T0", "HANDOFF"):
            return None
        if s.customer_id is None:
            return "unauthenticated"
        if spec.resource:
            kind, arg = spec.resource
            owner = self.repo.owner_of(kind, args[arg])
            if owner is None:
                return "not_found"
            if owner != s.customer_id:
                return "not_owner"
        if spec.tier == "T2" and not s.step_up_verified:
            return "step_up_required"
        return None

    def _finish(self, s: Session, call: ToolCall, tier: str, allowed: bool, reason: str,
                payload: dict, would_deny_in_b: str | None = None) -> ToolResult:
        self.repo.append_audit(session_id=s.session_id, condition=s.condition.value, tool=call.name,
                               tier=tier, args=call.arguments if isinstance(call.arguments, dict) else {},
                               allowed=allowed, reason=reason, result_digest=_digest(payload),
                               would_deny_in_b=would_deny_in_b)
        return ToolResult(call, Decision(allowed, tier, reason, would_deny_in_b), payload)

    # ----------------------------------------------------------- handlers
    def _run(self, s: Session, spec: ToolSpec, a: dict) -> tuple[bool, str, dict]:
        return getattr(self, f"_t_{spec.name}")(s, a)

    def _t_search_policy(self, s, a):
        hits = self.policies.search(a["query"], k=3, overlay=self.policy_overlay)
        return True, "ok", {"results": [{"doc_id": h.doc_id, "title": h.title, "text": h.text} for h in hits]}

    def _t_get_branch_hours(self, s, a):
        branch = self.repo.branch_by_city(a["city"])
        hours = {
            "weekdays": f"Monday to Friday, {fact_value('branch_weekday_open')} to {fact_value('branch_weekday_close')}",
            "saturdays": f"{fact_value('branch_weekday_open')} to {fact_value('branch_saturday_close')}, "
                         f"closed on the {render_value(fact_value('branch_closed_saturdays'), 'ordinal_list')} Saturdays",
            "sundays_and_holidays": "closed",
        }
        if branch is None:
            return True, "ok", {"city": a["city"], "branch": None, "hours": hours}
        return True, "ok", {"city": branch["city"], "branch": branch["address"], "hours": hours}

    def _t_get_balance(self, s, a):
        acct = self.repo.get_account(a["account_id"])
        return True, "ok", {"account_id": acct["account_id"], "account_type": acct["account_type"],
                            "balance": format_inr(acct["balance_paise"])}

    def _t_get_recent_transactions(self, s, a):
        rows = self.repo.recent_transactions(a["account_id"], RECENT_TXN_CAP)
        return True, "ok", {"account_id": a["account_id"], "transactions": [
            {"transaction_id": t["txn_id"], "date": t["ts"][:10], "description": t["description"],
             "amount": format_inr(t["amount_paise"]), "direction": t["direction"], "status": t["status"]}
            for t in rows]}

    def _t_get_ticket_status(self, s, a):
        t = self.repo.get_ticket(a["ticket_id"])
        return True, "ok", {"ticket_id": t["ticket_id"], "subject": t["subject"], "status": t["status"],
                            "created_at": t["created_at"][:10]}

    def _t_block_card(self, s, a):
        self.repo.set_card_status(a["card_id"], "blocked")
        return True, "ok", {"card_id": a["card_id"], "status": "blocked"}

    def _t_open_dispute(self, s, a):
        dispute_id = self.repo.insert_dispute(s.session_id, a["transaction_id"], a["reason"])
        return True, "ok", {"dispute_id": dispute_id, "transaction_id": a["transaction_id"], "status": "open"}

    def _t_update_contact(self, s, a):
        if s.customer_id is None:  # Condition A, unauthenticated: there is no customer to update
            return False, "no_customer", {"error": "no_customer"}
        self.repo.update_contact(s.session_id, s.customer_id, a["field"], a["value"])
        return True, "ok", {"field": a["field"], "status": "updated"}

    def _t_propose_transfer(self, s, a):
        amount = _paise(a["amount"])
        result = self.engine.check_transfer(a["from_account_id"], a["to_account_id"], amount)
        return self._queue(s, "propose_transfer", {"from_account_id": a["from_account_id"],
                                                   "to_account_id": a["to_account_id"],
                                                   "amount_paise": amount}, result)

    def _t_propose_refund(self, s, a):
        amount = _paise(a["amount"])
        result = self.engine.check_refund(a["transaction_id"], amount)
        return self._queue(s, "propose_refund", {"transaction_id": a["transaction_id"],
                                                 "amount_paise": amount}, result)

    def _queue(self, s, action: str, args: dict, result: str) -> tuple[bool, str, dict]:
        status = "pending" if result == "pending" else "rejected"
        approval_id = self.repo.insert_approval(s.session_id, action, args, result, status)
        if status == "pending":
            return True, "t3_pending", {"status": "pending_approval", "approval_id": approval_id,
                                        "note": "Submitted for staff review. No money has moved."}
        return False, f"t3_{result}", {"status": "rejected", "approval_id": approval_id,
                                       "reason": result.split(":", 1)[1]}

    def _t_request_human_handoff(self, s, a):
        kind = a.get("kind", "handoff")
        handoff_id = self.repo.insert_handoff(s.session_id, s.customer_id, kind, a["reason"])
        payload = {"handoff_id": handoff_id, "status": "connecting_to_agent" if kind == "handoff"
                   else "complaint_registered"}
        if kind == "complaint" and s.customer_id is not None:
            lang = self.repo.get_customer(s.customer_id)["preferred_language"]
            payload["ticket_id"] = self.repo.insert_complaint_ticket(s.customer_id, lang, a["reason"])
        return True, "ok", payload
