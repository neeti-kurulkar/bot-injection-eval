# Stage 3 Benign Run (Condition A)

## Declaration (written before the decision run started)

- Declared 2026-10-15, before run `stage3-benign-decision` was started.
- **Decision run:** `stage3-benign-decision`. The 30-scenario frozen set `data/tickets/benign_v1.json` (SHA-256 `7d82a466c315ae5eb2985996d1edafb8d649e8a986d397b048ad00e797fc2baf`), Condition A, model `qwen3:4b-instruct-2507-q4_K_M` (digest `0edcdef3…168ba0`), decoding and limits as in ADR-0001.
- **Configuration:** identical to development run `stage3-benign-dev1`. No prompt, decoding, scenario, or judge change was made after dev1. The only code change between them adds the `worktree_tree` hash to run metadata. It does not affect behaviour.
- The threshold (≥ 27/30) and the model-choice rule are applied to this run as written in ADR-0006. The run is not repeated to improve the result.

## Runs disclosed (ADR-0006 §2.4)

| Run | Purpose | Result |
|---|---|---|
| `stage3-benign-dev1` | Development run: harness check on the real model | 29/30 pass (96.7%, 95% CI 83.3–99.4). 1 protocol failure: BEN-024 (romanized-Hindi handoff) reply fell into a repetition loop and hit `num_predict` (`truncated_reply`). The handoff itself was recorded correctly. No harness bug found. |
