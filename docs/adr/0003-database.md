# ADR-0003: Database — SQLite (stdlib), fresh copy per scenario

Status: Proposed (Stage 0 gate)

## Decision
- SQLite through Python's `sqlite3`. Foreign keys are on. Money is integer paise.
- The Stage 1 generator writes canonical JSON/CSV files to `data/world/` (ADR-0009). These are the byte-identical determinism artifact, because SQLite page layout is not guaranteed to be byte-stable across versions. Stage 2 builds the template `sahayak.db` from those files (gitignored, rebuilt on demand). *(Amended 2026-10-15, Stage 1: the DB build moved to Stage 2, where the schema lives.)*
- Each scenario runs on a fresh copy of the template (a temp file per scenario, deleted afterwards unless `--keep-db`). Overlays (attacker-written ticket or note) are inserted into that copy only.
- The audit log, approvals, and handoffs live in the per-scenario DB and are exported into the scenario's JSONL record before the copy is deleted.
- A repository layer (`mockbank/repo.py`) owns all SQL. The ToolLayer never writes SQL directly.

## Consequences
Scenarios are isolated and order-independent, which helps resumability. Copying a DB of a few MB takes milliseconds, which is negligible next to model latency.
