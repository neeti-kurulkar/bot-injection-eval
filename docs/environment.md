# Environment Record

Recorded 2026-10-15 with `scripts/record_env.ps1` and manual probes. Every results file repeats these values. If any value changes, add a dated row to the change log. Don't overwrite.

| Item | Value |
|---|---|
| OS | Windows 11 Home Single Language (10.0.26200) |
| CPU RAM | 23.7 GB usable (24 GB installed) |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU, 6141 MiB VRAM, driver 581.86 |
| Python (project venv) | CPython 3.13.11, pinned by `.python-version` = 3.13 (system Python 3.12.2 is not used) |
| uv | 0.13.1; lockfile `uv.lock` (pydantic 2.14.1, httpx 0.28.1, pytest 9.1.1) |
| Ollama | 0.40.4 |
| Endpoint | `http://localhost:11434/api/chat`, `stream:false` |
| **Model tag** | `qwen3:4b-instruct-2507-q4_K_M` (ADR-0001) |
| Model digest | `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` |
| Quantization | Q4_K_M |
| Parameters | 4.0B |
| `num_ctx` | 8192 (set explicitly in every request) |
| Decoding | temperature 0, per-scenario seed, num_predict 512, keep_alive 30m |
| Thinking | disabled: non-thinking instruct model, `/no_think` appended to every user turn, thinking-text validator on |
| Processor (`ollama ps`) | 100% GPU, 3.9 GB, context 8192 (2026-10-15) |

## Rejected candidate (kept for the record)

| Item | Value |
|---|---|
| Tag | `qwen3:4b` |
| Digest | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` |
| Quantization / context | Q4_K_M / 262144 |
| Identified as | Qwen3-4B thinking-2507 (template always opens `<think>`) |
| Probe result | `/no_think` ignored: a thinking trace was still produced. With `think:false`, reasoning leaked into `content` with a stray `</think>`. Processor 100% GPU at `num_ctx` 8192 (3.9 GB). |

## Change log
- 2026-10-15: initial record.
- 2026-10-15: uv 0.13.1 installed; `uv sync` created the venv on CPython 3.13.11, now pinned via `.python-version`.

## Selected-model probe (2026-10-15)
One neutral prompt (`What is 2+3? … /no_think`, temperature 0, seed 1): content `5`, `thinking` field absent, 2 output tokens. Ollama lists a `thinking` capability for this tag, but the template's `<think>` handling only applies to earlier assistant turns that carry reasoning content. The generation prompt does not open a think block. The thinking-text validator stays on regardless (ADR-0001). Modelfile defaults (temperature 0.7, top_p 0.8, top_k 20) are overridden per request with temperature 0.
- 2026-10-16: Ollama was not running at the start of the session and was started with `ollama serve`. Same version (0.40.4), and the model digest still matches the pin (checked by `tests/model`). All Stage 6 held-out and Stage 7 runs used this server.
