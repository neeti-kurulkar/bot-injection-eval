"""Deterministic T3 policy engine. Kept in both conditions: it is a core-bank control.

Every T3 outcome is either 'pending' (queued for a human) or 'rejected:<rule>'.
Nothing executes here.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sahayak.generate.policy_corpus import fact_value
from sahayak.mockbank.repo import Repository

AS_OF = datetime(2026, 10, 1, 10, 0)


class PolicyEngine:
    def __init__(self, repo: Repository, as_of: datetime = AS_OF):
        self.repo = repo
        self.as_of = as_of
        self.daily_limit = fact_value("online_transfer_daily_limit") * 100
        self.cooling = timedelta(hours=fact_value("new_beneficiary_cooling_hours"))
        self.cooling_cap = fact_value("new_beneficiary_limit_cooling") * 100

    def check_transfer(self, from_account_id: str, to_account_id: str, amount_paise: int) -> str:
        if amount_paise <= 0:
            return "rejected:non_positive_amount"
        src = self.repo.get_account(from_account_id)
        if src is None:
            return "rejected:unknown_source_account"
        if from_account_id == to_account_id:
            return "rejected:same_account"
        # The beneficiary must be registered by the owner of the source account.
        ben = self.repo.beneficiary(src["customer_id"], to_account_id)
        if ben is None:
            return "rejected:beneficiary_not_registered"
        if amount_paise > self.daily_limit:
            return "rejected:over_daily_limit"
        added = datetime.fromisoformat(ben["added_on"])
        if self.as_of - added < self.cooling and amount_paise > self.cooling_cap:
            return "rejected:new_beneficiary_cooling"
        if amount_paise > src["balance_paise"]:
            return "rejected:insufficient_funds"
        return "pending"

    def check_refund(self, transaction_id: str, amount_paise: int) -> str:
        if amount_paise <= 0:
            return "rejected:non_positive_amount"
        txn = self.repo.get_transaction(transaction_id)
        if txn is None:
            return "rejected:unknown_transaction"
        if txn["direction"] != "debit" or txn["status"] != "posted":
            return "rejected:not_a_posted_debit"
        if amount_paise > txn["amount_paise"]:
            return "rejected:exceeds_original_amount"
        return "pending"
