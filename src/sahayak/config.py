"""All project settings. Env-driven (prefix SAHAYAK_), no secrets.

Pinned model values mirror docs/environment.md and ADR-0001.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str) -> str:
    return os.environ.get(f"SAHAYAK_{name}", default)


@dataclass(frozen=True)
class Settings:
    # Synthetic world (Stage 1)
    seed: int = 20261015
    data_dir: Path = REPO_ROOT / "data"

    # Model (ADR-0001). The digest is checked against /api/tags before real runs.
    ollama_url: str = "http://localhost:11434"
    model_tag: str = "qwen3:4b-instruct-2507-q4_K_M"
    model_digest: str = "0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0"
    num_ctx: int = 8192
    temperature: float = 0.0
    num_predict: int = 512
    keep_alive: str = "30m"
    max_steps: int = 6
    max_output_tokens_per_turn: int = 1500

    @property
    def world_dir(self) -> Path:
        return self.data_dir / "world"


def load_settings() -> Settings:
    return Settings(
        seed=int(_env("SEED", str(Settings.seed))),
        data_dir=Path(_env("DATA_DIR", str(REPO_ROOT / "data"))),
        ollama_url=_env("OLLAMA_URL", Settings.ollama_url),
        model_tag=_env("MODEL_TAG", Settings.model_tag),
        model_digest=_env("MODEL_DIGEST", Settings.model_digest),
        num_ctx=int(_env("NUM_CTX", str(Settings.num_ctx))),
    )
