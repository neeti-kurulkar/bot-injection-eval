"""Live tests against the local Ollama server. Skipped if the server or the pinned model is missing."""

from __future__ import annotations

import httpx
import pytest

from sahayak.agent.backend import OllamaClient
from sahayak.agent.context import NO_THINK
from sahayak.config import load_settings

S = load_settings()


def _available() -> bool:
    try:
        tags = httpx.get(f"{S.ollama_url}/api/tags", timeout=2).json()["models"]
        return any(m["name"] == S.model_tag for m in tags)
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _available(), reason="Ollama not running or pinned model not pulled")

BALANCE_TOOL = {"type": "function", "function": {
    "name": "get_balance", "description": "Balance of one of the customer's accounts.",
    "parameters": {"type": "object", "properties": {"account_id": {"type": "string"}}, "required": ["account_id"]}}}


def test_pinned_digest_and_metadata():
    meta = OllamaClient(S, seed=1).metadata()
    assert meta["digest_matches_pin"], meta
    assert meta["quantization"] == "Q4_K_M" and meta["num_ctx"] == 8192


def test_no_thinking_with_no_think():
    turn = OllamaClient(S, seed=1).chat(
        [{"role": "user", "content": f"What is 2+3? Answer with one number.\n{NO_THINK}"}], [])
    assert turn.protocol_failures == [] and turn.content.strip() == "5"


def test_tool_round_trip_on_real_model():
    client = OllamaClient(S, seed=1)
    msgs = [{"role": "system", "content": "You are a bank assistant. The signed-in customer owns account A0001."},
            {"role": "user", "content": f"What is my balance?\n{NO_THINK}"}]
    first = client.chat(msgs, [BALANCE_TOOL])
    assert first.protocol_failures == []
    assert [c.name for c in first.tool_calls] == ["get_balance"]
    assert first.tool_calls[0].arguments == {"account_id": "A0001"}
    msgs += [{"role": "assistant", "content": first.content,
              "tool_calls": [{"function": {"name": "get_balance", "arguments": {"account_id": "A0001"}}}]},
             {"role": "tool", "tool_name": "get_balance", "content": '{"balance": "₹12,340.00"}'}]
    second = client.chat(msgs, [BALANCE_TOOL])
    assert second.protocol_failures == [] and not second.tool_calls
    assert "12,340" in second.content
