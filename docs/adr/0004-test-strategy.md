# ADR-0004: Test strategy

Status: Proposed (Stage 0 gate)

## Decision
| Suite | Needs model? | Content |
|---|---|---|
| `tests/unit` | no | Tier rules, ownership checks, OTP mock, PolicyEngine, audit writer, guard rules, data-marking escaping, BM25, judges (fixtures per language), Wilson CI, `/no_think` appending, reply validator |
| `tests/integration` | no | Mock bank + ToolLayer end to end under both conditions, approval queue, handoff, per-scenario DB isolation |
| `tests/eval` | no (StubBackend) | Runner resumability (kill and resume), JSONL schema, metrics on a scripted stub, cost ledger arithmetic |
| `tests/model` | yes (local Ollama) | Real `/api/chat` round trip with one tool call; reply validator on real output; metadata capture. Skipped automatically if `localhost:11434` is unreachable or the pinned tag is missing. |

- **StubBackend**: a scripted `ModelBackend` that returns predetermined `AssistantTurn`s (including thinking-text and malformed tool-call cases), so the agent loop and judges can be tested without a model.
- A ToolLayer test failure blocks the stage (spec Section 8). Nothing gets worked around in the LLM layer.
- `pytest -q` with no model running must pass, with model tests skipped.
- The Stage 2 must-pass cases are listed in [tier-enforcement-test-plan.md](../design/tier-enforcement-test-plan.md).
- No coverage-percentage target. The test plan's case list is the bar.
