# ADR-0001: Model backend — Ollama, qwen3:4b-instruct-2507-q4_K_M

Status: Accepted (user decision, 2026-10-15)

## Context
The spec (Section 0.1) requires one local model served by Ollama on `localhost:11434`, with thinking disabled through a trailing `/no_think` on every user turn. The default tag given was `qwen3:4b`, with `qwen3:8b` as fallback.

A protocol probe on 2026-10-15 (one non-scenario prompt, "What is 2+3?") found:
- The installed `qwen3:4b` (digest `359d7dd4bcda…`, Q4_K_M, 262144 native context) is the Qwen3-4B **thinking-2507** variant. Its chat template always opens a `<think>` block.
- With `/no_think` alone: the reply content was `5`, but Ollama returned a 158-character thinking trace.
- With `/no_think` and `think:false`: the thinking field was empty, but the reasoning text leaked into `content`, ending with a stray `</think>`.

Under the Section 0.1 validation rule, nearly every reply would be a protocol failure. The study would be measuring the template mismatch, not injection.

## Decision
- Model: **`qwen3:4b-instruct-2507-q4_K_M`**. Same parameter count and quantization, non-thinking instruct variant with tool calling. The user approved this in chat on 2026-10-15. It replaces the spec's `qwen3:4b` default.
- `/no_think` is still appended to every user turn, as Section 0.1 requires, and a unit test checks it. For this model it is an inert marker. Thinking-text validation stays on and logs any `<think>`/`</think>` or a non-empty `thinking` field as a protocol failure.
- Pinned digest: `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` (Q4_K_M, 4.0B). Probe on 2026-10-15: content `5`, no thinking field, 100% GPU at `num_ctx` 8192 (3.9 GB).
- Requests do not set `think`. Ollama lists a `thinking` capability for this tag, but the instruct checkpoint does not produce reasoning and its generation prompt opens no think block. So `/no_think` plus validation is the whole mechanism. Adding `think` later would need a new ADR.
- Fallback: `qwen3:8b`, used only under the ADR-0006 rule. Before any fallback run, its template and a `/no_think` probe must be checked the same way and recorded here. At Q4_K_M (~5.2 GB) it may not fit 100% on GPU in 6 GB VRAM with `num_ctx 8192`. Any split is recorded.
- Transport: native `POST /api/chat`, `stream:false`. Tool results go back as `role:"tool"` messages. `httpx` client with explicit timeouts. Retries (max 2, only on connection errors or HTTP 5xx) are logged per call.
- Decoding: `temperature 0`, `seed` per scenario, `num_ctx 8192`, `num_predict 512`, `keep_alive "30m"`. These override the Modelfile defaults so results are reproducible. GPU nondeterminism is measured in Stage 3.
- Pinned and recorded in config and in every results file: tag, full digest from `/api/tags`, quantization, Ollama version, `num_ctx`, decoding options, and the `ollama ps` processor string.

## Consequences
- The study's model is the instruct-2507 checkpoint, not the April 2025 hybrid Qwen3-4B. Results are specific to it.
- The thinking-2507 model stays installed but is unused. It can be removed with `ollama rm qwen3:4b` if disk space matters.
