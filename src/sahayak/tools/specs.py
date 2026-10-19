"""Tool catalogue: tier, argument schema, and the resource each tool touches.

Argument schemas are strict: unknown arguments are rejected. No tool has an
argument that names the session, customer, tier, or step-up state.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    type: str  # "string" | "number"
    description: str
    required: bool = True
    enum: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolSpec:
    name: str
    tier: str  # "T0".."T3" | "HANDOFF"
    description: str
    params: dict[str, Param]
    resource: tuple[str, str] | None = None  # (kind, argument) whose owner must match in B


TOOLS: dict[str, ToolSpec] = {t.name: t for t in (
    ToolSpec("search_policy", "T0", "Search Sahayak Bank policy documents.",
             {"query": Param("string", "What to look up")}),
    ToolSpec("get_branch_hours", "T0", "Branch working hours for a city.",
             {"city": Param("string", "City name")}),
    ToolSpec("get_balance", "T1", "Balance of one of the customer's accounts.",
             {"account_id": Param("string", "Account ID, e.g. A0001")}, ("account", "account_id")),
    ToolSpec("get_recent_transactions", "T1", "Last 5 transactions of one of the customer's accounts.",
             {"account_id": Param("string", "Account ID")}, ("account", "account_id")),
    ToolSpec("get_ticket_status", "T1", "Status of one of the customer's support tickets.",
             {"ticket_id": Param("string", "Ticket ID")}, ("ticket", "ticket_id")),
    ToolSpec("block_card", "T2", "Permanently block one of the customer's cards. Needs OTP verification.",
             {"card_id": Param("string", "Card ID, e.g. CARD-0001")}, ("card", "card_id")),
    ToolSpec("open_dispute", "T2", "Open a dispute on one of the customer's transactions. Needs OTP verification.",
             {"transaction_id": Param("string", "Transaction ID"),
              "reason": Param("string", "Short reason")}, ("transaction", "transaction_id")),
    ToolSpec("update_contact", "T2", "Change the customer's registered phone or email. Needs OTP verification.",
             {"field": Param("string", "Which detail", enum=("phone", "email")),
              "value": Param("string", "New value")}),
    ToolSpec("propose_transfer", "T3",
             "Propose a transfer for staff approval. Does not move money.",
             {"from_account_id": Param("string", "Source account ID"),
              "to_account_id": Param("string", "Destination account ID"),
              "amount": Param("number", "Amount in rupees")}, ("account", "from_account_id")),
    ToolSpec("propose_refund", "T3",
             "Propose a refund of a transaction for staff approval. Does not move money.",
             {"transaction_id": Param("string", "Transaction ID"),
              "amount": Param("number", "Amount in rupees")}, ("transaction", "transaction_id")),
    ToolSpec("request_human_handoff", "HANDOFF",
             "Hand the conversation to a human agent, or register a complaint. Always available.",
             {"reason": Param("string", "Why the customer wants a human"),
              "kind": Param("string", "handoff or complaint", required=False, enum=("handoff", "complaint"))}),
)}

RESTRICTED_ALLOWED = frozenset({"search_policy", "get_branch_hours", "request_human_handoff"})

# ADR-0014: opt-in tool for the structured-facts variants only (not part of A, B or the ablations).
FACT_TOOL = ToolSpec("get_policy_fact", "T0",
                     "Official value of a bank policy number (fee, charge, limit, rate, deadline, timing) from the "
                     "bank's policy records.",
                     {"query": Param("string", "What the customer is asking about, e.g. 'contactless limit'")})


def validate_args(spec: ToolSpec, args: object) -> str | None:
    """Return an error string, or None if the arguments are valid."""
    if not isinstance(args, dict):
        return "arguments must be an object"
    extra = sorted(set(args) - set(spec.params))
    if extra:
        return f"unknown arguments: {', '.join(extra)}"
    for name, p in spec.params.items():
        if name not in args:
            if p.required:
                return f"missing argument: {name}"
            continue
        v = args[name]
        if p.type == "string" and not isinstance(v, str):
            return f"{name} must be a string"
        if p.type == "number" and (isinstance(v, bool) or not isinstance(v, (int, float))):
            return f"{name} must be a number"
        if p.enum and v not in p.enum:
            return f"{name} must be one of {', '.join(p.enum)}"
    return None


def ollama_schema(spec: ToolSpec) -> dict:
    props = {}
    for name, p in spec.params.items():
        props[name] = {"type": p.type, "description": p.description}
        if p.enum:
            props[name]["enum"] = list(p.enum)
    return {"type": "function", "function": {
        "name": spec.name, "description": spec.description,
        "parameters": {"type": "object", "properties": props,
                       "required": [n for n, p in spec.params.items() if p.required]}}}
