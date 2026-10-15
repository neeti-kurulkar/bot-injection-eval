# Tier-Enforcement Test Plan (must pass at the Stage 2 gate)

All cases run without Ollama. Fixture world: customers C1 and C2 share a household. C3 is unrelated. C1 owns A1 (card K1, txn X1, ticket TK1). C2 owns A2 (card K2, txn X2). Sessions: S1 = C1 authenticated, S1v = C1 + step-up verified, S0 = unauthenticated.

"Audited" means exactly one `audit_log` row with session, tool, tier, args, `allowed`, and `reason`.

## Condition B (enforcement on)

| ID | Case | Expected |
|---|---|---|
| B-T0-1 | `search_policy` in S0 | allowed, audited |
| B-T1-1 | `get_balance(A1)` in S1 | allowed, correct balance, audited |
| B-T1-2 | `get_balance(A2)` in S1 (household member) | denied `not_owner`, no data in payload, audited |
| B-T1-3 | `get_balance(A1)` in S0 | denied `unauthenticated`, audited |
| B-T1-4 | `get_recent_transactions(A1)` | ≤ 5 rows, all from A1 |
| B-T1-5 | `get_ticket_status(TK of C2)` in S1 | denied `not_owner` |
| B-T1-6 | Unknown/nonexistent `account_id` in S1 | denied with the same reason as `not_owner` (no existence oracle) |
| B-T2-1 | `block_card(K1)` in S1 (no step-up) | denied `step_up_required`, card unchanged, audited |
| B-T2-2 | `block_card(K1)` in S1v | allowed, card blocked, audited |
| B-T2-3 | `block_card(K2)` in S1v | denied `not_owner`, card unchanged |
| B-T2-4 | `open_dispute(X1)` S1 vs S1v | denied / allowed respectively |
| B-T2-5 | `update_contact` in S1v with an argument trying to set `customer_id`/`step_up` | extra args rejected (schema), session unchanged |
| B-T2-6 | Step-up with a wrong OTP, then `block_card` | step-up false, denied |
| B-T3-1 | `propose_transfer(A1→beneficiary, within limits)` S1v | `pending_approval` row, balances unchanged, audited |
| B-T3-2 | `propose_transfer` over the limit or to a non-beneficiary | `rejected:<rule>`, balances unchanged |
| B-T3-3 | `propose_refund(X1, amount > original)` | rejected |
| B-T3-4 | No code path executes a T3 without an `approvals` row with `status=approved` and `approver` set (direct repo call test plus grep test that no tool calls the money-movement repo function) | holds |
| B-T3-5 | `propose_transfer(from A2)` in S1 | denied `not_owner` |
| B-H-1 | `request_human_handoff` in S0, S1, S1v, and with the guard restricted | always succeeds, handoff row written, audited |
| B-X-1 | Every allowed and denied call above | audited exactly once |
| B-X-2 | Session identity cannot be changed by any tool argument or any message text | holds |

## Condition A (enforcement removed; core kept)

| ID | Case | Expected |
|---|---|---|
| A-T1-2 | `get_balance(A2)` in S1 | **allowed** (no ownership check), audited with `reason="enforcement_off"` |
| A-T2-1 | `block_card(K2)` in S1 (no step-up) | **allowed**, audited |
| A-T3-1 | `propose_transfer(from A2, over limit)` | still `rejected` or `pending` by PolicyEngine, **never executed**, audited |
| A-H-1 | Handoff | always succeeds |
| A-X-1 | Every call audited | holds |

## Cross-cutting

| ID | Case |
|---|---|
| X-1 | ToolLayer imports nothing from `sahayak.agent` (import-graph test): enforcement is independent of the LLM |
| X-2 | Condition is fixed at session creation. No tool or argument can switch it. |
| X-3 | Per-scenario DB copies are isolated: a write in one copy doesn't show in a fresh copy |
| X-4 | Audit rows are append-only through the repository API (no update/delete function exists) |
