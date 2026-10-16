"""LLMAgent: tool-calling loop over a ModelBackend.

One customer turn = up to `max_steps` model calls. Each tool call goes through
the ToolLayer, and the result is fed back as a role "tool" message. The loop
ends on a reply with no tool calls ("final"), on the step limit
("step_limit"), on the output-token budget ("token_budget"), or on a backend
error ("error"). Limit hits are recorded as outcomes, never hidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sahayak.agent.backend import AssistantTurn, BudgetExceeded, ModelBackend
from sahayak.agent.context import ContextBuilder
from sahayak.domain.models import ToolCall
from sahayak.tools.layer import ToolLayer


@dataclass
class TurnResult:
    reply: str
    outcome: str  # final | step_limit | token_budget | error
    steps: list[dict] = field(default_factory=list)  # one per model call
    protocol_failures: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def model_calls(self) -> int:
        return len(self.steps)


class LLMAgent:
    def __init__(self, backend: ModelBackend, tools: ToolLayer, context: ContextBuilder,
                 max_steps: int, max_output_tokens: int):
        self.backend = backend
        self.tools = tools
        self.context = context
        self.max_steps = max_steps
        self.max_output_tokens = max_output_tokens

    def run_turn(self, session_id: str, messages: list[dict], restricted: bool = False) -> TurnResult:
        """Runs one customer turn. `messages` already ends with the user turn; it is extended in place."""
        schemas = self.tools.schemas(restricted)
        known = {s["function"]["name"] for s in schemas}
        result = TurnResult(reply="", outcome="step_limit")
        out_tokens = 0
        for _ in range(self.max_steps):
            try:
                turn: AssistantTurn = self.backend.chat(messages, schemas)
            except BudgetExceeded:
                raise  # the spending cap stops the whole run, not just this scenario
            except Exception as e:  # noqa: BLE001 - recorded, scenario continues to be judged
                result.outcome, result.error = "error", f"{type(e).__name__}: {e}"
                return result
            out_tokens += turn.cost.eval_count
            step = {"assistant": turn.to_record(), "tool_results": []}
            result.steps.append(step)
            result.protocol_failures.extend(turn.protocol_failures)
            if turn.done_reason == "length":
                result.protocol_failures.append("truncated_reply")

            if not turn.tool_calls:
                result.reply, result.outcome = turn.content, "final"
                return result

            messages.append({"role": "assistant", "content": turn.content,
                             "tool_calls": [{"function": {"name": c.name, "arguments": c.arguments},
                                             **({"id": c.id} if c.id else {})}
                                            for c in turn.tool_calls]})
            for c in turn.tool_calls:
                if c.name not in known:
                    result.protocol_failures.append("unknown_tool_name")
                args = c.arguments if isinstance(c.arguments, dict) else {}
                r = self.tools.execute(session_id, ToolCall(c.name, args), restricted=restricted)
                if r.decision.reason == "invalid_arguments":
                    result.protocol_failures.append("invalid_tool_arguments")
                step["tool_results"].append({"name": c.name, "arguments": c.arguments,
                                             "allowed": r.decision.allowed, "reason": r.decision.reason,
                                             "would_deny_in_b": r.decision.would_deny_in_b,
                                             "payload": r.payload})
                tool_msg = self.context.tool_message(c.name, r.payload)
                if c.id:
                    tool_msg["tool_call_id"] = c.id
                messages.append(tool_msg)

            if out_tokens >= self.max_output_tokens:
                result.outcome = "token_budget"
                return result
        return result
