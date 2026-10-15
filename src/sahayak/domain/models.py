"""Domain records for the synthetic Sahayak Bank world. Money is integer paise."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class Tier(IntEnum):
    T0 = 0
    T1 = 1
    T2 = 2
    T3 = 3


LANGUAGES = ("en", "hinglish", "hi-Deva", "hi-Latn")


@dataclass(frozen=True)
class Customer:
    customer_id: str
    display_name: str
    household_id: str
    city: str
    is_metro: bool
    phone: str
    email: str
    preferred_language: str
    kyc_risk: str


@dataclass(frozen=True)
class Account:
    account_id: str
    customer_id: str  # exactly one owner
    account_type: str  # savings | salary | current
    branch_city: str
    opened_on: str
    opening_balance_paise: int
    balance_paise: int
    status: str


@dataclass(frozen=True)
class Card:
    card_id: str
    account_id: str
    variant: str  # classic | platinum
    last4: str
    expiry: str  # YYYY-MM
    status: str  # active | blocked


@dataclass(frozen=True)
class Transaction:
    txn_id: str
    account_id: str
    ts: str  # ISO local time, no zone
    amount_paise: int  # always positive; see direction
    direction: str  # debit | credit
    txn_type: str
    description: str
    channel: str
    status: str  # posted | failed


@dataclass(frozen=True)
class Beneficiary:
    beneficiary_id: str
    customer_id: str
    nickname: str
    account_ref: str  # internal account_id or EXT-...
    bank: str
    added_on: str


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    customer_id: str
    created_at: str
    category: str
    language: str
    subject: str
    body: str
    status: str


@dataclass(frozen=True)
class AccountNote:
    note_id: str
    account_id: str
    author: str
    created_at: str
    body: str


@dataclass(frozen=True)
class Branch:
    branch_id: str
    city: str
    is_metro: bool
    address: str


@dataclass(frozen=True)
class PolicyFact:
    fact_id: str
    doc_id: str
    key: str
    value: int | float | str | list[int]
    unit: str
    rendered: str
    description: str


# ------------------------------------------------------------------ runtime
class Condition(str, Enum):
    A = "A"  # baseline, system under study: tier and ownership enforcement off
    B = "B"  # defended, under evaluation: enforcement on


@dataclass(frozen=True)
class Session:
    session_id: str
    condition: Condition
    customer_id: str | None  # None = unauthenticated
    step_up_verified: bool


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict


@dataclass(frozen=True)
class Decision:
    allowed: bool
    tier: str  # "T0".."T3" or "HANDOFF"
    reason: str
    would_deny_in_b: str | None = None  # Condition A: the check B would have failed


@dataclass(frozen=True)
class ToolResult:
    call: ToolCall
    decision: Decision
    payload: dict
