"""Hosted model backends for the comparison study (ADR-0013): Sarvam and OpenAI.

This is the only module that may name a hosted endpoint (the repo hygiene test
allowlists it). Both providers speak OpenAI-style Chat Completions with tools.

Safety rails:
  - API keys come from the environment or the git-ignored .env file. They are
    sent only in request headers and never appear in metadata, records, or logs.
  - A spending cap is checked before every call against a persistent ledger
    (data/runs/_spend/<provider>.json). A call that could cross the cap raises
    BudgetExceeded, which stops the run; rerunning resumes it.
  - Thinking is turned off; reasoning tokens are recorded, and any returned
    reasoning text counts as the `thinking_field` protocol failure.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from sahayak.agent.backend import AssistantTurn, BudgetExceeded, CallCost, validate_reply
from sahayak.config import REPO_ROOT, Settings


@dataclass(frozen=True)
class Provider:
    name: str
    model: str
    base_url: str
    key_env: str
    currency: str
    input_per_m: float  # uncached input, per 1M tokens (cache writes included, ADR-0013)
    cached_per_m: float
    output_per_m: float
    tax: float  # multiplier applied to the token cost
    default_budget: float
    budget_env: str


PROVIDERS = {
    # ₹15 / ₹5 cached / ₹60 per 1M, plus 18% GST (pricing page, 2026-10-16).
    "sarvam": Provider("sarvam", "sarvam-105b", "https://api.sarvam.ai/v1", "SARVAM_API_KEY", "INR",
                       15.0, 5.0, 60.0, 1.18, 90.0, "SAHAYAK_BUDGET_SARVAM_INR"),
    # $0.20 / $0.02 cached / $1.20 per 1M; uncached input counted at 1.25x for cache writes.
    "openai": Provider("openai", "gpt-5.6-luna", "https://api.openai.com/v1", "OPENAI_API_KEY", "USD",
                       0.20 * 1.25, 0.02, 1.20, 1.0, 2.20, "SAHAYAK_BUDGET_OPENAI_USD"),
}

EST_CHARS_PER_TOKEN = 3  # conservative (Devanagari tokenises densely)


def call_cost(p: Provider, prompt_tokens: int, cached_tokens: int, completion_tokens: int) -> float:
    uncached = max(0, prompt_tokens - cached_tokens)
    raw = (uncached * p.input_per_m + cached_tokens * p.cached_per_m + completion_tokens * p.output_per_m) / 1e6
    return raw * p.tax


def load_api_key(env_name: str, env_file: Path = REPO_ROOT / ".env") -> str:
    """Environment first, then the git-ignored .env file. Never logged."""
    if os.environ.get(env_name):
        return os.environ[env_name]
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.strip().partition("=")
            if sep and k.strip().removeprefix("export ").strip() == env_name:
                return v.strip().strip('"').strip("'")
    raise RuntimeError(f"{env_name} is not set (environment or .env)")


class SpendLedger:
    """Running total per provider, persisted after every call so caps hold across runs."""

    def __init__(self, path: Path, currency: str):
        self.path = path
        self.currency = currency
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.spent = float(data.get("spent", 0.0))
        self.calls = int(data.get("calls", 0))
        self.write_errors: list[str] = []

    def add(self, amount: float) -> None:
        """Never raises: the call is already paid for, so a failed write must not fail the scenario.
        The in-memory total still enforces the cap; the next successful write persists it."""
        self.spent += amount
        self.calls += 1
        text = json.dumps({"currency": self.currency, "spent": round(self.spent, 6), "calls": self.calls,
                           "updated_at": datetime.now(timezone.utc).isoformat()}, indent=1) + "\n"
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(text, encoding="utf-8")
        except OSError as e:
            self.write_errors.append(f"{type(e).__name__}: {e}")
            return
        # On Windows the target can be briefly locked (antivirus, indexer, an open editor): retry.
        for attempt in range(5):
            try:
                tmp.replace(self.path)
                return
            except PermissionError as e:
                if attempt == 4:
                    self.write_errors.append(f"{type(e).__name__}: {e}")
                    return
                time.sleep(0.2 * (attempt + 1))


def to_wire(messages: list[dict]) -> list[dict]:
    """Internal (Ollama-style) messages -> Chat Completions messages."""
    out = []
    for m in messages:
        if m["role"] == "assistant" and m.get("tool_calls"):
            out.append({"role": "assistant", "content": m.get("content") or None,
                        "tool_calls": [{"id": c.get("id", ""), "type": "function",
                                        "function": {"name": c["function"]["name"],
                                                     "arguments": json.dumps(c["function"]["arguments"],
                                                                             ensure_ascii=False)}}
                                       for c in m["tool_calls"]]})
        elif m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": m.get("tool_call_id", ""), "content": m["content"]})
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out


class HostedChatClient:
    """Chat Completions client for one provider. Same interface as OllamaClient."""

    MAX_RETRIES = 4
    wants_no_think = False  # /no_think is a Qwen command (ADR-0013)

    def __init__(self, provider: str, settings: Settings, seed: int = 0, http: httpx.Client | None = None,
                 ledger: SpendLedger | None = None, budget: float | None = None, api_key: str | None = None):
        self.p = PROVIDERS[provider]
        self.name = provider
        self.s = settings
        self.seed = seed
        self._key = api_key or load_api_key(self.p.key_env)
        self.http = http or httpx.Client(base_url=self.p.base_url, timeout=httpx.Timeout(120.0, connect=10.0))
        self.ledger = ledger or SpendLedger(settings.data_dir / "runs" / "_spend" / f"{provider}.json",
                                            self.p.currency)
        self.budget = budget if budget is not None else float(os.environ.get(self.p.budget_env,
                                                                             self.p.default_budget))
        self.seen_models: set[str] = set()
        self.fingerprints: set[str] = set()

    def __repr__(self) -> str:  # keep the key out of any accidental repr
        return f"HostedChatClient({self.name!r}, model={self.p.model!r})"

    def _headers(self) -> dict:
        if self.name == "sarvam":
            return {"api-subscription-key": self._key}
        return {"Authorization": f"Bearer {self._key}"}

    def _body(self, messages: list[dict], tools: list[dict]) -> dict:
        body = {"model": self.p.model, "messages": to_wire(messages), "tools": tools}
        if self.name == "sarvam":
            body.update(temperature=self.s.temperature, max_tokens=self.s.num_predict, reasoning_effort=None)
        else:  # reasoning models: no temperature
            body.update(max_completion_tokens=self.s.num_predict, reasoning_effort="none")
        return body

    def estimate(self, body: dict) -> float:
        """Worst case for one call: every input token uncached, full output budget used."""
        chars = len(json.dumps(body["messages"], ensure_ascii=False)) + len(json.dumps(body["tools"]))
        return call_cost(self.p, chars // EST_CHARS_PER_TOKEN, 0, self.s.num_predict)

    def _post(self, body: dict) -> tuple[dict, int, list[str]]:
        log: list[str] = []
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                r = self.http.post("/chat/completions", json=body, headers=self._headers())
                if r.status_code == 429 or r.status_code >= 500:
                    raise httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
                r.raise_for_status()
                return r.json(), attempt, log
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                status = getattr(getattr(e, "response", None), "status_code", 0)
                if isinstance(e, httpx.HTTPStatusError) and status < 500 and status != 429:
                    raise
                log.append(f"attempt {attempt + 1}: {type(e).__name__}: HTTP {status or '-'}")
                if attempt == self.MAX_RETRIES:
                    raise
                time.sleep(min(30.0, 2.0 * 2 ** attempt))
        raise AssertionError("unreachable")

    def chat(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        body = self._body(messages, tools)
        est = self.estimate(body)
        if self.ledger.spent + est > self.budget:
            raise BudgetExceeded(f"{self.name}: spent {self.ledger.spent:.4f} {self.p.currency}, next call up to "
                                 f"{est:.4f}, cap {self.budget:.2f}")
        t0 = time.perf_counter()
        data, retries, log = self._post(body)
        wall = time.perf_counter() - t0

        usage = data.get("usage") or {}
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        cached = int((usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
        reasoning = int((usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
        cost = call_cost(self.p, prompt, cached, completion)
        self.ledger.add(cost)
        if data.get("model"):
            self.seen_models.add(str(data["model"]))
        if data.get("system_fingerprint"):
            self.fingerprints.add(str(data["system_fingerprint"]))

        choice = (data.get("choices") or [{}])[0]
        msg = dict(choice.get("message") or {})
        msg["thinking"] = msg.get("reasoning_content") or msg.get("reasoning") or ""
        content, calls, failures = validate_reply(msg)
        ids = [str(tc.get("id", "")) for tc in msg.get("tool_calls") or []]
        calls = [type(c)(c.name, c.arguments, i) for c, i in zip(calls, ids)]
        finish = choice.get("finish_reason") or ""
        return AssistantTurn(content, calls, failures, "length" if finish == "length" else finish,
                             CallCost(prompt_eval_count=prompt, eval_count=completion, wall_clock_s=round(wall, 3),
                                      retries=retries, cached_tokens=cached, reasoning_tokens=reasoning,
                                      cost=round(cost, 8), cost_currency=self.p.currency), log)

    def with_seed(self, seed: int) -> HostedChatClient:
        c = HostedChatClient(self.name, self.s, seed, self.http, self.ledger, self.budget, self._key)
        c.seen_models, c.fingerprints = self.seen_models, self.fingerprints  # shared across scenarios
        return c

    def metadata(self) -> dict:
        """Recorded in every results file. Never includes the API key."""
        return {
            "backend": self.name,
            "provider": self.name,
            "model_tag": self.p.model,
            "model_returned": sorted(self.seen_models),
            "system_fingerprints": sorted(self.fingerprints),
            "model_digest": None,
            "digest_matches_pin": None,
            "pinnable": False,
            "base_url": self.p.base_url,
            "temperature": self.s.temperature if self.name == "sarvam" else "not sent",
            "max_output_tokens_per_call": self.s.num_predict,
            "thinking": "reasoning_effort=null" if self.name == "sarvam" else "reasoning_effort=none",
            "prices_per_1m": {"input": self.p.input_per_m, "cached": self.p.cached_per_m,
                              "output": self.p.output_per_m, "tax_multiplier": self.p.tax,
                              "currency": self.p.currency},
            "budget_cap": self.budget,
            "spent_so_far": round(self.ledger.spent, 6),
            "ledger_write_errors": len(self.ledger.write_errors),
            "quantization": None,
            "num_ctx": None,
            "processor": "hosted API",
            "ollama_version": None,
        }
