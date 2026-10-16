# ADR-0013: Hosted-model comparison (amends spec rules 5 and 6)

Status: Accepted (user decision, 2026-10-16). Infrastructure only; no hosted run has been made yet.

## Context
The study ran on one local model (Qwen3 4B). Its Hindi weakness and the unsolved planted-policy problem raise an obvious question: do larger or Hindi-specialised models behave differently under the same attacks? Answering it needs hosted APIs. The original spec forbade them:
- Rule 5: no hosted AI API.
- Rule 6: attack payloads are never sent to any external service.

## Decision
1. **Rules 5 and 6 are amended for a model-comparison study only.**
   - Two hosted providers may be called: **Sarvam** (`sarvam-105b`) and **OpenAI** (`gpt-5.6-luna`).
   - The synthetic attack suite, the benign look-alikes, and the synthetic bank data may be sent to them in API requests.
   - **No real data is ever sent.** Everything in the requests is synthetic (Stage 1).
   - Attack payloads are still not published anywhere else. Docs keep the "categories, not payloads" rule.
2. **Local Qwen3 4B stays the reference.** Its results, and the pre-registered decisions made on it, are unchanged.
3. **API keys** are read only from environment variables, loaded from a git-ignored `.env` at the repo root (`SARVAM_API_KEY`, `OPENAI_API_KEY`).
   - They are never written to logs, run records, metadata, or the repository.
   - `tests/unit/test_repo_hygiene.py` keeps scanning for key-like strings.
4. **Endpoints:** hosted endpoints appear only in `src/sahayak/agent/hosted.py`, which the hygiene test allowlists. All other model traffic stays on `localhost`.
5. **Thinking off, matching the reference.**
   - Sarvam gets `reasoning_effort: null`, which per its docs disables reasoning.
   - OpenAI gets `reasoning_effort: "none"`.
   - Reasoning tokens are recorded on every call. Any visible thinking text is still a protocol failure.
   - `/no_think` is a Qwen command, so it is appended only for the Ollama backend.
6. **Budget guard.** Each provider has a hard spending cap, checked before every call against a persistent spend ledger in `data/runs/_spend/<provider>.json`.
   - **Defaults:** Sarvam ₹90 including GST, against a ₹100 credit; OpenAI $2.20, against a $2.50 credit.
   - **Override:** `SAHAYAK_BUDGET_SARVAM_INR` and `SAHAYAK_BUDGET_OPENAI_USD`.
   - **When the cap is reached, the run stops** rather than continuing. It is resumable.
   - **Prices:** Sarvam ₹15 / ₹60 / ₹5 per 1M input / output / cached tokens, plus 18% GST (from the user's pricing-page screenshot, 2026-10-16). OpenAI $0.20 / $1.20 / $0.02 per 1M, with cache writes counted at 1.25× input to stay conservative (OpenAI docs, 2026-10-16).
7. **Same protocol for every model.**
   - Same scenarios, prompt base, tools, judges, and limits (6 steps, 512 output tokens per call).
   - Each model must first pass the 30-scenario benign check (≥ 27/30, ADR-0006) before its attack results are reported.
   - Planned scope: benign, dev A and B, and held-out A and B. Ablations stay Qwen-only, for budget reasons.
8. **Determinism and reproducibility.**
   - Hosted models cannot be pinned by digest. Each record stores the provider, model ID, the `model` value the API returns, and `system_fingerprint` where given.
   - Temperature 0 is requested from Sarvam. OpenAI reasoning models may not accept a temperature, so it is not sent. Results are therefore less reproducible than the local reference, and reports must say so.
9. **Held-out reuse.** The held-out families have already been run once per condition on Qwen. Running them on other models does not tune the defense, which stays frozen, so the comparison remains fair. But these attacks are no longer "never seen" in the strict sense, and reports must state this. A fresh sealed held-out set is the cleaner option and is left as a follow-up.

## Consequences
- Estimated cost of the planned scope: about ₹75 on Sarvam and about $1 on OpenAI. The figures come from the measured 2,500 input / 135 output tokens per scenario. The benign check gives the real per-scenario cost before the attack runs.
- Results from hosted models depend on provider-side changes that cannot be reproduced exactly later.
