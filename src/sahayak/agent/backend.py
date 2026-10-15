"""Model backends: the Ollama client (the only code that talks to the model) and a
scripted stub for tests. Both return AssistantTurn records.

Protocol failures are detected and recorded, never silently repaired:
  thinking_field       Ollama returned a non-empty `thinking` field
  thinking_text        content contains <think> / </think>
  malformed_tool_call  tool-call text left in content, or a tool call with non-object arguments
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Protocol

import httpx

from sahayak.config import Settings

THINK_RE = re.compile(r"</?think>", re.IGNORECASE)
TOOL_TEXT_RE = re.compile(r"<tool_call>|\"name\"\s*:\s*\"\w+\"\s*,\s*\"arguments\"", re.IGNORECASE)


@dataclass(frozen=True)
class CallCost:
    prompt_eval_count: int = 0
    eval_count: int = 0
    prompt_eval_duration_ns: int = 0
    eval_duration_ns: int = 0
    total_duration_ns: int = 0
    load_duration_ns: int = 0
    wall_clock_s: float = 0.0
    retries: int = 0


@dataclass(frozen=True)
class ModelToolCall:
    name: str
    arguments: object  # dict when well-formed


@dataclass(frozen=True)
class AssistantTurn:
    content: str
    tool_calls: list[ModelToolCall]
    protocol_failures: list[str]
    done_reason: str
    cost: CallCost
    retry_log: list[str] = field(default_factory=list)

    def to_record(self) -> dict:
        return asdict(self)


class ModelBackend(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> AssistantTurn: ...
    def metadata(self) -> dict: ...


def validate_reply(message: dict) -> tuple[str, list[ModelToolCall], list[str]]:
    """Parse an Ollama assistant message into (content, tool calls, protocol failures)."""
    failures: list[str] = []
    content = message.get("content") or ""
    if (message.get("thinking") or "").strip():
        failures.append("thinking_field")
    if THINK_RE.search(content):
        failures.append("thinking_text")
    if TOOL_TEXT_RE.search(content):
        failures.append("malformed_tool_call")
    calls = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, str):  # some runtimes return a JSON string
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                pass
        if not isinstance(args, dict):
            failures.append("malformed_tool_call")
        calls.append(ModelToolCall(str(fn.get("name", "")), args))
    return content, calls, sorted(set(failures), key=failures.index)


class OllamaClient:
    """POST /api/chat on localhost only, stream:false, explicit num_ctx, logged retries."""

    MAX_RETRIES = 2

    def __init__(self, settings: Settings, seed: int = 0, http: httpx.Client | None = None):
        if not settings.ollama_url.startswith(("http://localhost", "http://127.0.0.1")):
            raise ValueError("Ollama must be reached on localhost only (Section 0.1)")
        self.s = settings
        self.seed = seed
        self.http = http or httpx.Client(base_url=settings.ollama_url,
                                         timeout=httpx.Timeout(300.0, connect=5.0))

    def _post(self, path: str, body: dict) -> tuple[dict, int, list[str]]:
        log: list[str] = []
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                r = self.http.post(path, json=body)
                if r.status_code >= 500:
                    raise httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
                r.raise_for_status()
                return r.json(), attempt, log
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                status = getattr(getattr(e, "response", None), "status_code", 0)
                if isinstance(e, httpx.HTTPStatusError) and status < 500:
                    raise
                log.append(f"attempt {attempt + 1}: {type(e).__name__}: {e}")
                if attempt == self.MAX_RETRIES:
                    raise
                time.sleep(1.0 * (attempt + 1))
        raise AssertionError("unreachable")

    def chat(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        body = {
            "model": self.s.model_tag,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "keep_alive": self.s.keep_alive,
            "options": {"num_ctx": self.s.num_ctx, "temperature": self.s.temperature,
                        "seed": self.seed, "num_predict": self.s.num_predict},
        }
        t0 = time.perf_counter()
        data, retries, log = self._post("/api/chat", body)
        wall = time.perf_counter() - t0
        content, calls, failures = validate_reply(data.get("message") or {})
        cost = CallCost(
            prompt_eval_count=data.get("prompt_eval_count", 0),
            eval_count=data.get("eval_count", 0),
            prompt_eval_duration_ns=data.get("prompt_eval_duration", 0),
            eval_duration_ns=data.get("eval_duration", 0),
            total_duration_ns=data.get("total_duration", 0),
            load_duration_ns=data.get("load_duration", 0),
            wall_clock_s=round(wall, 3),
            retries=retries,
        )
        return AssistantTurn(content, calls, failures, data.get("done_reason", ""), cost, log)

    def with_seed(self, seed: int) -> OllamaClient:
        return OllamaClient(self.s, seed, self.http)

    def metadata(self) -> dict:
        """Pinned values recorded in every results file (Section 0.1)."""
        version = self.http.get("/api/version").json().get("version")
        tags = self.http.get("/api/tags").json().get("models", [])
        m = next((x for x in tags if x["name"] == self.s.model_tag), None)
        ps = self.http.get("/api/ps").json().get("models", [])
        loaded = next((x for x in ps if x["name"] == self.s.model_tag), None)
        processor = None
        if loaded:
            size, vram = loaded.get("size", 0), loaded.get("size_vram", 0)
            processor = "100% GPU" if size and vram >= size else f"{round(100 * vram / size)}% GPU / CPU split"
        return {
            "backend": "ollama",
            "ollama_version": version,
            "model_tag": self.s.model_tag,
            "model_digest": m["digest"] if m else None,
            "pinned_digest": self.s.model_digest,
            "digest_matches_pin": bool(m and m["digest"] == self.s.model_digest),
            "quantization": m["details"]["quantization_level"] if m else None,
            "num_ctx": self.s.num_ctx,
            "temperature": self.s.temperature,
            "num_predict": self.s.num_predict,
            "keep_alive": self.s.keep_alive,
            "thinking": "disabled (/no_think on every user turn; non-thinking instruct model)",
            "processor": processor,
        }


class StubBackend:
    """Scripted backend for tests. `script` maps the call index (or a function of the
    message list) to an Ollama-style assistant message dict."""

    def __init__(self, script: Sequence[dict] | Callable[[list[dict], int], dict]):
        self.script = script
        self.calls: list[list[dict]] = []

    def chat(self, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        i = len(self.calls)
        self.calls.append([dict(m) for m in messages])
        msg = self.script(messages, i) if callable(self.script) else self.script[min(i, len(self.script) - 1)]
        content, calls, failures = validate_reply(msg)
        n_out = max(1, len(content) // 4 + 10 * len(calls))
        cost = CallCost(prompt_eval_count=sum(len(str(m.get("content", ""))) for m in messages) // 4,
                        eval_count=n_out, eval_duration_ns=n_out * 10_000_000, total_duration_ns=n_out * 10_000_000)
        return AssistantTurn(content, calls, failures, "stop", cost)

    def with_seed(self, seed: int) -> StubBackend:
        return StubBackend(self.script)  # fresh call counter per scenario

    def metadata(self) -> dict:
        return {"backend": "stub", "model_tag": "stub", "model_digest": None, "num_ctx": None,
                "processor": None, "ollama_version": None}
