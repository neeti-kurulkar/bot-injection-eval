"""Hosted backends (ADR-0013), tested against an in-process mock transport. No network calls."""

from __future__ import annotations

import json

import httpx
import pytest

from sahayak.agent.backend import BudgetExceeded
from sahayak.agent.context import NO_THINK, ContextBuilder
from sahayak.agent.hosted import PROVIDERS, HostedChatClient, SpendLedger, call_cost, load_api_key
from sahayak.agent.loop import LLMAgent
from sahayak.config import Settings
from sahayak.domain.models import Condition
from tests.conftest import corpus_store

FAKE_KEY = "test-key-not-real"


def reply(content="", tool_calls=None, usage=None, finish="stop", **msg_extra):
    msg = {"role": "assistant", "content": content, **msg_extra}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {"model": "returned-model", "system_fingerprint": "fp_1",
            "choices": [{"message": msg, "finish_reason": finish}],
            "usage": usage or {"prompt_tokens": 1000, "completion_tokens": 100,
                               "prompt_tokens_details": {"cached_tokens": 200},
                               "completion_tokens_details": {"reasoning_tokens": 0}}}


def client(provider, tmp_path, responses, budget=100.0):
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json=responses[min(len(seen) - 1, len(responses) - 1)])
    http = httpx.Client(base_url="http://mock.invalid/v1", transport=httpx.MockTransport(handler))
    s = Settings(data_dir=tmp_path)
    c = HostedChatClient(provider, s, http=http, ledger=SpendLedger(tmp_path / "spend.json", "X"),
                         budget=budget, api_key=FAKE_KEY)
    return c, seen


@pytest.mark.parametrize("provider", ["sarvam", "openai"])
def test_request_format(provider, tmp_path):
    c, seen = client(provider, tmp_path, [reply("hi")])
    c.chat([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], [])
    body = json.loads(seen[0].content)
    assert body["model"] == PROVIDERS[provider].model
    if provider == "sarvam":
        assert seen[0].headers["api-subscription-key"] == FAKE_KEY
        assert "reasoning_effort" in body and body["reasoning_effort"] is None
        assert body["temperature"] == 0.0 and body["max_tokens"] == 512
    else:
        assert seen[0].headers["authorization"] == f"Bearer {FAKE_KEY}"
        assert body["reasoning_effort"] == "none" and body["max_completion_tokens"] == 512
        assert "temperature" not in body


def test_cost_and_ledger(tmp_path):
    c, _ = client("sarvam", tmp_path, [reply("hi")])
    t = c.chat([{"role": "user", "content": "u"}], [])
    expected = (800 * 15 + 200 * 5 + 100 * 60) / 1e6 * 1.18
    assert t.cost.cost == pytest.approx(expected) and t.cost.cost_currency == "INR"
    assert t.cost.cached_tokens == 200 and t.cost.prompt_eval_count == 1000
    assert json.loads((tmp_path / "spend.json").read_text())["spent"] == pytest.approx(expected)
    assert SpendLedger(tmp_path / "spend.json", "INR").spent == pytest.approx(expected)  # persists


def test_openai_cache_writes_counted_conservatively():
    p = PROVIDERS["openai"]
    assert call_cost(p, 1_000_000, 0, 0) == pytest.approx(0.25)
    assert call_cost(p, 0, 0, 1_000_000) == pytest.approx(1.20)


def test_budget_stops_before_the_call(tmp_path):
    c, seen = client("openai", tmp_path, [reply("hi")], budget=0.0001)
    with pytest.raises(BudgetExceeded):
        c.chat([{"role": "user", "content": "u" * 3000}], [])
    assert seen == []  # nothing was sent


def test_reasoning_text_is_a_protocol_failure(tmp_path):
    c, _ = client("sarvam", tmp_path, [reply("hi", reasoning_content="let me think")])
    assert "thinking_field" in c.chat([{"role": "user", "content": "u"}], []).protocol_failures


def test_length_finish_is_recorded(tmp_path):
    c, _ = client("openai", tmp_path, [reply("cut", finish="length")])
    assert c.chat([{"role": "user", "content": "u"}], []).done_reason == "length"


def test_metadata_never_contains_the_key(tmp_path):
    c, _ = client("openai", tmp_path, [reply("hi")])
    c.chat([{"role": "user", "content": "u"}], [])
    m = c.metadata()
    assert FAKE_KEY not in json.dumps(m) and FAKE_KEY not in repr(c)
    assert m["model_returned"] == ["returned-model"] and m["system_fingerprints"] == ["fp_1"]
    assert m["pinnable"] is False


def test_tool_call_ids_round_trip_through_the_loop(bank, tmp_path):
    first = reply("", tool_calls=[{"id": "call_7", "type": "function",
                                   "function": {"name": "get_balance", "arguments": '{"account_id": "A1"}'}}])
    c, seen = client("openai", tmp_path, [first, reply("Your balance is ₹50,000.00.")])
    s = bank.session(Condition.A, "C1")
    cb = ContextBuilder(bank.repo, corpus_store(), data_marking=False, seed=5, no_think=c.wants_no_think)
    msgs = cb.initial_messages("C1", "balance?")
    r = LLMAgent(c, bank.tools, cb, 6, 1500).run_turn(s.session_id, msgs)
    assert r.outcome == "final" and r.reply.startswith("Your balance")
    wire = json.loads(seen[1].content)["messages"]
    assert wire[-2]["tool_calls"][0]["id"] == "call_7"
    assert json.loads(wire[-2]["tool_calls"][0]["function"]["arguments"]) == {"account_id": "A1"}
    assert wire[-1] == {"role": "tool", "tool_call_id": "call_7", "content": wire[-1]["content"]}
    assert not any(NO_THINK in (m.get("content") or "") for m in wire)  # Qwen-only command


def test_key_loaded_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("SOME_TEST_KEY", raising=False)
    f = tmp_path / ".env"
    f.write_text('OTHER=1\nSOME_TEST_KEY="abc123"\n', encoding="utf-8")
    assert load_api_key("SOME_TEST_KEY", f) == "abc123"
    with pytest.raises(RuntimeError):
        load_api_key("MISSING_TEST_KEY", f)


@pytest.mark.parametrize("provider", ["sarvam", "openai"])
def test_cli_builds_hosted_backend_without_calling_it(provider, tmp_path, monkeypatch, capsys):
    from sahayak import cli

    monkeypatch.setenv(PROVIDERS[provider].key_env, FAKE_KEY)
    b = cli._backend(provider, Settings(data_dir=tmp_path))
    assert isinstance(b, HostedChatClient) and b.wants_no_think is False
    assert FAKE_KEY not in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["run-eval", "--help"])
    assert provider in capsys.readouterr().out
