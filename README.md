# Sahayak Bank support-bot injection study

A research measurement study. It measures how often a local LLM support bot for a **fictional** bank (Sahayak Bank) can be steered by attacker-controllable text into fabricating policy, leaking another customer's data, blocking a human handoff, or taking actions it should not. It also measures how much one defense (in-code tier enforcement plus data marking plus a rule-based input screen) reduces those failures, and what that costs in false blocks.

Condition A is the system under study. Condition B is a defense under evaluation. Neither is claimed to be secure. All data is synthetic, the bank API is a local mock, and the only model is a local Ollama model.

Status: **Stage 0 (design)**. See [docs/design/system-design.md](docs/design/system-design.md), [docs/threat-model.md](docs/threat-model.md), [docs/adr/](docs/adr/).

## Setup (Windows PowerShell)

```powershell
pip install uv                      # or the official uv installer
uv sync
uv run python -c "import sahayak; print(sahayak.__version__)"
ollama pull qwen3:4b-instruct-2507-q4_K_M
powershell -ExecutionPolicy Bypass -File scripts\record_env.ps1
```

## Stage 1: synthetic world

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stage1.ps1            # generate, verify, test
powershell -ExecutionPolicy Bypass -File scripts\stage1.ps1 -Samples   # also print sample records
```

This prints record counts and the world SHA-256 (the hash of `data/world/MANIFEST.sha256`). Policy sources: [docs/policy-sources.md](docs/policy-sources.md).

## Stage 2: mock bank and tool layer (no model)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stage2.ps1
```

Builds `data/world/sahayak.db` (gitignored) from the world files, runs `pytest tests/unit tests/integration`, and prints a scripted Condition A versus B walk-through of the ToolLayer.

Per-stage run instructions will be added as each stage lands.
