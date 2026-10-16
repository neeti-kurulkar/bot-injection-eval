# Sahayak Bank support-bot injection study

**What this is.** A research measurement study, not a product.
- It measures how often a local LLM support bot for a **fictional** bank (Sahayak Bank) can be steered by attacker-controllable text into five failures:
  - stating a planted wrong policy number
  - revealing another customer's balance
  - not handing off to a human when asked
  - making unauthorized card or contact changes
  - proposing transfers nobody asked for
- It also measures how much one defense reduces those failures, and at what cost in false blocks.
- **Condition A** is the system under study. **Condition B** (in-code tier and ownership checks, data marking, and a rule-based input guard) is a defense under evaluation.
- Neither is claimed to be secure. All data is synthetic, the bank API is a local SQLite mock, and the only model is one local Ollama model. Results describe this prototype under the stated setup and nothing more.

**Main result (held-out attack families):**
- Any-goal attack success was **27.6%** in A and **13.6%** in B: −14.0 points (95% CI 8.6–19.6), with no measured false blocks on benign look-alikes.
- **Fabricated policy did not improve** (52% → 56%).

Full report: [docs/results/final.md](docs/results/final.md).

## Setup (Windows 11, PowerShell)

1. **Ollama** (the study used 0.40.4). Install from ollama.com, or update an existing install by re-running the installer. Check with `ollama --version`. Ollama must be running; if `localhost:11434` does not answer, start it with `ollama serve` in a separate window.
2. **Pinned model.** Do not use plain `qwen3:4b`: that tag is a thinking-only variant, rejected in ADR-0001.
   ```powershell
   ollama pull qwen3:4b-instruct-2507-q4_K_M
   ```
   The digest must be `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`. The runner refuses to run otherwise.
3. **Python environment** (uv, Python 3.13 pinned by `.python-version`):
   ```powershell
   pip install uv
   uv sync
   ```
4. **Environment record.** This prints the OS, GPU, Python, Ollama version, model digest, thinking check, and GPU placement. Compare it with [docs/environment.md](docs/environment.md).
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\record_env.ps1
   ```
   `ollama ps` should show `100% GPU`. Any CPU/GPU split is recorded in each run's metadata.

## Reproduce

Every run is resumable: re-running the same command continues where it stopped.

```powershell
# Everything that needs no model: world determinism, mock bank, all tests, stub runs of every pipeline (~2 min)
powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend stub

# Benign subset on the local model: 30 scenarios, checked against the pre-registered threshold (~1.5 min)
powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend ollama -Scope benign

# Development attack suite on the local model: A, B, B-nomark, B-noguard (~75 min)
powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend ollama -Scope dev
```

**Held-out runs** use the sealed families. Run them once per condition, only as a deliberate gate decision (spec rule 7):
```powershell
$env:SAHAYAK_HELDOUT_APPROVED = 'stage5-heldout-gate-approved'
powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend ollama -Scope heldout   # A then B (~25 min)
```

Expected runtimes and model use, measured on an RTX 4050 Laptop GPU (6 GB):

| Run | Scenarios | Time | Model calls per scenario | Tokens per scenario (prompt / output) |
|---|---|---|---|---|
| Benign, A | 30 | ~80 s | 1.7 | ~2,500 / 130 |
| Dev, A | 420 | ~22 min | 1.6 | ~2,500 / 136 |
| Dev, B / B-nomark / B-noguard | 420 each | ~17 / 18 / 22 min | 1.4–1.7 | ~1,300–3,000 / 110–140 |
| Held-out, A / B | 268 each | ~14 / 11 min | 1.6 / 1.4 | ~2,480 / 135; ~1,970 / 111 |

Output throughput is about 58 tokens/s. Reply wording is not fully reproducible across separate runs at temperature 0 (21/30 identical in the Stage 3 check), but tool decisions were (30/30). Expect small differences in rates.

## Results dashboard

A local, read-only Streamlit view of the published results (bound to `localhost`; held-out runs show totals only; injected attack text hidden by default).

```powershell
uv sync --group dashboard
uv run streamlit run dashboard/app.py
```

## Hosted-model comparison (ADR-0013)

Results: [docs/results/model-comparison.md](docs/results/model-comparison.md) (held-out, any goal, A → B: Qwen 27.6% → 13.6%, Sarvam 13.6% → 3.1%, GPT-5.6 Luna 25.0% → 6.1%). Spend: ₹74.52 and $0.63.

Sarvam `sarvam-105b` and OpenAI `gpt-5.6-luna` can be run on the same protocol as the local reference. Keys go in a git-ignored `.env` at the repo root (`SARVAM_API_KEY`, `OPENAI_API_KEY`). A spending cap (Sarvam ₹90, OpenAI $2.20; override with `SAHAYAK_BUDGET_SARVAM_INR` / `SAHAYAK_BUDGET_OPENAI_USD`) is checked before every call against `data/runs/_spend/<provider>.json`; hitting it stops the run, and rerunning resumes.

Benign check first (≥ 27/30 before attack results count), then dev and held-out A/B. Publish as `compare-<model>-<run>` so the dashboard's Model comparison tab picks them up (`<model>` = `sarvam-105b` or `gpt-5.6-luna`; `<run>` = `benign`, `A-dev`, `B-dev`, `A-heldout`, `B-heldout`):

```powershell
uv run python -m sahayak.cli run-benign --backend sarvam --run-id sarvam-benign --publish compare-sarvam-105b-benign
uv run python -m sahayak.cli run-eval --backend sarvam --suite dev --condition A --run-id sarvam-A-dev
uv run python -m sahayak.cli summarize-eval --run-id sarvam-A-dev --publish compare-sarvam-105b-A-dev
```

## Stages and where things are

| Stage | What | Script | Key docs |
|---|---|---|---|
| 0 | Design, threat model, ADRs, pre-registration | `scripts/record_env.ps1` | [system-design.md](docs/design/system-design.md), [threat-model.md](docs/threat-model.md), [docs/adr/](docs/adr/) |
| 1 | Seeded synthetic world, 40 policies, 108 structured facts | `scripts/stage1.ps1` | [policy-sources.md](docs/policy-sources.md), ADR-0009 |
| 2 | Mock bank and tier-enforcing ToolLayer (no model) | `scripts/stage2.ps1` | [tier-enforcement-test-plan.md](docs/design/tier-enforcement-test-plan.md) |
| 3 | Bot runtime, pre-registered benign decision run | `scripts/stage3_benign.ps1` | [stage3-benign.md](docs/results/stage3-benign.md), ADR-0010 |
| 4 | Frozen attack + look-alike suite, sealed held-out split | `scripts/stage4.ps1` | [stage4-suite.md](docs/results/stage4-suite.md), ADR-0011 |
| 5 | Baseline (A) dev and held-out | `scripts/eval_baseline.ps1` | [baseline.md](docs/results/baseline.md), [judge-validation.md](docs/judge-validation.md) |
| 6 | Defended (B), ablations, held-out | `scripts/eval_defended.ps1` | [defended.md](docs/results/defended.md), ADR-0012 |
| 7 | Final report, RBI mapping, reproduction | `scripts/reproduce.ps1` | [final.md](docs/results/final.md), [rbi-mapping.md](docs/rbi-mapping.md) |

Code is in `src/sahayak/`:
- `mockbank/`: SQLite schema and repository
- `tools/`: ToolLayer, sessions and OTP, T3 policy engine
- `agent/`: Ollama client, context builder, tool loop
- `guard/`: rule guard
- `generate/`: world, benign set, attack suite
- `eval/`: runner, judges, metrics, statistics, comparison

Run records are written to `data/runs/` (gitignored). Attack payloads live only in `data/attacks/`; held-out items are sealed.

## Limitations (summary)

Synthetic data, a mock bank, and a single local model at one quantization with thinking disabled. Four language variants and eight attack families, all single-shot. Small samples, with one run per condition. Only numeric policy fabrication is measured. All templates were written by one agent before the split. The numeric spot-check sheet is not yet labelled.

This is not a red-team engagement against any real system and does not replace one. No compliance with any regulation is claimed; [docs/rbi-mapping.md](docs/rbi-mapping.md) only relates design choices to the RBI FREE-AI recommendations. Full limitations: [final.md](docs/results/final.md#limitations).
