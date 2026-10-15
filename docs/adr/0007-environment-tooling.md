# ADR-0007: Environment and dependency tooling

Status: Accepted (user decision, 2026-10-15)

## Decision
- `uv` manages the environment (`uv sync`, `uv run`). The user installs uv (it was not present on 2026-10-15). `uv.lock` is committed once generated.
- Python ≥ 3.11 (the machine has 3.12.2).
- Runtime dependencies: `pydantic` (scenario/record schemas) and `httpx` (Ollama client). Dev: `pytest`. Nothing else without a new ADR.
- Build backend: `hatchling`, src layout (`src/sahayak`).
- All scripts are Windows PowerShell 5.1-compatible `.ps1` files under `scripts/`.
- `data/runs/` is gitignored.
