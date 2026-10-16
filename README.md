# Sahayak Bank support-bot injection study

A research measurement study, not a product. It measures how often planted text can steer an LLM support bot for a **fictional** bank, how much one defense reduces that, and how three models compare.

- **Plain-language overview:** [docs/overview.html](docs/overview.html) (open it in a browser)
- **Full report:** [docs/results/final.md](docs/results/final.md)
- **Model comparison:** [docs/results/model-comparison.md](docs/results/model-comparison.md)

All data is synthetic and the bank is a local SQLite mock. Condition A is the system under study; Condition B is a defense under evaluation. Neither is claimed to be secure, and results describe this prototype under its stated setup only.

## What it does

**The bot (Condition A).** "Sahayak" answers signed-in customers using eleven tools in four tiers: T0 policy search and branch hours, T1 own balance, transactions and tickets, T2 card block, dispute and contact change (owner plus OTP), and T3 transfer and refund *proposals* (a policy engine and a human approval queue decide). Its prompt includes the customer's recent tickets, account notes and matching policy excerpts. In A the tool layer runs whatever the model asks.

**The defense (Condition B)** adds three things to the same bot:
1. **Checks in code:** ownership, sign-in and OTP are verified in the tool layer against the session, never the conversation.
2. **Data marking:** untrusted text is wrapped in random-ID `DATA` blocks, and the prompt says that text is information, not instructions.
3. **An input guard:** nine text rules. A hit limits that turn to FAQ tools and the handoff.

**The attacks.** 608 single-turn attacks with five goals (planted wrong policy, another customer's balance, blocked handoff, unauthorized card or contact change, unrequested transfer). They are planted in four places (the customer's message, a past ticket, an account note, a policy document) and written in English, Hinglish, Devanagari Hindi and romanized Hindi. There are also 80 benign look-alikes. Three of the eight technique families were sealed until the defense was finished; those held-out results are the estimate.

## Results

Held-out attack families, share of 228 attacks that worked (headline scoring rules):

| Model | A · no defense | B · defense on | A − B (95% CI) | Benign gate |
|---|---|---|---|---|
| Qwen3 4B (local) | 27.6% | 13.6% | +14.0 pts (8.6–19.6) | 29/30 |
| Sarvam 105B (hosted) | 13.6% | 3.1% | +10.5 pts (6.2–15.4) | 29/30 |
| GPT-5.6 Luna (hosted) | 25.0% | 6.1% | +18.9 pts (13.9–24.3) | 30/30 |

- **The code checks behaved the same on every model.** Under B there were no leaked balances, no unauthorized card or contact changes and no unrequested transfers, across 1,824 attack scenarios.
- **Planted policy is the main remaining failure.** It didn't fall on Qwen (25 → 27 of 48). It fell on Sarvam (13 → 6) and GPT (16 → 11), and it worked more often in Hindi than in English.
- **No benign look-alike was falsely blocked** on any model.
- **No money moved in any run.**

Caveats: one run per model and condition, and hosted models can't be pinned. The held-out families had already been run on Qwen before the hosted runs. See [model-comparison.md](docs/results/model-comparison.md).

## Setup (Windows 11, PowerShell)

1. **Python environment** (uv, Python 3.13 pinned by `.python-version`):
   ```powershell
   pip install uv
   uv sync
   ```
2. **Ollama**, for the local model (the study used 0.40.4). It must be running on `localhost:11434`; if it isn't answering, run `ollama serve` in another window. Pull the pinned model (not plain `qwen3:4b`, which is a thinking-only variant):
   ```powershell
   ollama pull qwen3:4b-instruct-2507-q4_K_M
   ```
   Its digest must be `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`; the runner refuses to run otherwise.
3. **Environment record** (optional). This prints the OS, GPU, Ollama version, model digest and GPU placement, for comparison with [docs/environment.md](docs/environment.md):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\record_env.ps1
   ```
4. **Hosted models** (optional, only for the comparison). Create a `.env` file at the repo root; it is git-ignored. Put your keys in it:
   ```
   SARVAM_API_KEY=...
   OPENAI_API_KEY=...
   ```

## Reproduce

Every run is resumable: rerunning the same command continues where it stopped.

```powershell
# No model needed: world determinism, mock bank, all tests, stub runs of every pipeline (~2 min)
powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend stub

# Local model, benign gate: 30 scenarios against the pre-registered threshold (~1.5 min)
powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend ollama -Scope benign

# Local model, development attack suite: A, B, B-nomark, B-noguard (~75 min)
powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend ollama -Scope dev
```

**Held-out runs** use the sealed families. Run each condition once per model, as a deliberate decision:
```powershell
$env:SAHAYAK_HELDOUT_APPROVED = 'stage5-heldout-gate-approved'
powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend ollama -Scope heldout   # A then B (~25 min)
```
Held-out runs print nothing until they finish, and report totals only.

**Hosted models** use the same CLI with `--backend sarvam` or `--backend openai`. Run the benign gate first, then dev and held-out A and B. Publish each run as `compare-<model>-<run>`, where `<model>` is `sarvam-105b` or `gpt-5.6-luna` and `<run>` is `benign`, `A-dev`, `B-dev`, `A-heldout` or `B-heldout`. The dashboard picks these up.
```powershell
uv run python -m sahayak.cli run-benign --backend sarvam --run-id sarvam-benign --publish compare-sarvam-105b-benign
uv run python -m sahayak.cli run-eval --backend sarvam --suite dev --condition A --run-id sarvam-A-dev
uv run python -m sahayak.cli summarize-eval --run-id sarvam-A-dev --publish compare-sarvam-105b-A-dev
uv run python -m sahayak.cli compare-variants --base sarvam-A-dev --runs sarvam-B-dev --publish compare-sarvam-105b-B-vs-A-dev
```

Rules for hosted runs:
- **Spending cap.** Each provider has a hard cap, checked before every call against `data/runs/_spend/<provider>.json`. The defaults are ₹90 and $2.20; override them with `SAHAYAK_BUDGET_SARVAM_INR` and `SAHAYAK_BUDGET_OPENAI_USD`.
- **One job per provider at a time.** Two processes on the same provider would undercount spend. Different providers can run in parallel.
- **Cost.** The full comparison cost ₹74.52 on Sarvam and $0.63 on OpenAI, for 1,411 scenarios each.

Typical times per scenario: Qwen on an RTX 4050 laptop GPU (6 GB) about 3 s, Sarvam about 1.0–1.3 s, GPT-5.6 Luna about 2.3–3.2 s.

## Results dashboard

A local, read-only Streamlit view, bound to `localhost`. Held-out runs show totals only, and injected attack text is hidden by default.

```powershell
uv sync --group dashboard
uv run streamlit run dashboard/app.py
```

It has tabs for the overview, the paired A-vs-B comparison, the ablation, language and surface breakdowns, the benign gate, the model comparison, and a transcript explorer (development runs only).

## Tests

```powershell
uv run pytest tests -q
```

The tests use no network. Hosted clients are tested against a mock transport. The repo checks fail if API keys, hosted endpoints outside `src/sahayak/agent/hosted.py`, attack payload text, or "secure/compliant" claims that are not negated appear in tracked files.

## Where things are

| Path | What |
|---|---|
| `src/sahayak/mockbank/` | SQLite schema and repository |
| `src/sahayak/tools/` | Tool layer (tier and ownership checks), sessions and OTP, T3 policy engine |
| `src/sahayak/agent/` | Context builder (data marking), tool loop, Ollama client, hosted clients with spend ledger |
| `src/sahayak/guard/` | The nine-rule input guard |
| `src/sahayak/generate/` | Synthetic world, benign set, attack suite and sealed split |
| `src/sahayak/eval/` | Runner, deterministic judges, metrics, statistics, paired comparison |
| `dashboard/` | Streamlit results dashboard |
| `data/world/`, `data/tickets/`, `data/attacks/` | Synthetic world, benign set, frozen attack suite (held-out sealed) |
| `data/runs/` | Per-scenario run records (gitignored) |
| `docs/design/`, `docs/adr/` | System design and the 13 decision records |
| `docs/results/` | Published summaries and reports |

The study ran in gated stages. Each stage has a script in `scripts/` and a results note in `docs/results/`:
- **Stage 0:** design and pre-registration
- **Stage 1:** synthetic world
- **Stage 2:** mock bank and tool layer
- **Stage 3:** bot and benign gate
- **Stage 4:** frozen attack suite
- **Stage 5:** baseline
- **Stage 6:** defense and ablations
- **Stage 7:** final report
- **Afterwards:** the hosted-model comparison (ADR-0013)

## Limitations

- Synthetic data and a mock bank.
- Single-turn, non-adaptive attacks.
- One run per model and condition, with small per-goal and per-language cells.
- Only numeric policy fabrication is measured.
- The prompt and guard were built on Qwen.
- Hosted models aren't pinnable.
- The judges were spot-checked on Qwen only, and the 66-item spot-check sheet isn't labelled yet.

This is not a red-team engagement against any real system. No regulatory compliance is claimed; [docs/rbi-mapping.md](docs/rbi-mapping.md) only relates design choices to the RBI FREE-AI recommendations. Full limitations: [final.md](docs/results/final.md#limitations).
