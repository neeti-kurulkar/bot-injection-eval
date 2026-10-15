# ADR-0009: Synthetic world format and generation rules

Status: Proposed (Stage 1 gate)

## Decision
- **Seed:** `20261015` (`SAHAYAK_SEED` overrides it). One `random.Random` stream, consumed in a fixed order.
- **Output:** `data/world/`, checked in, about 5 MB. Files:
  - `customers`, `accounts`, `cards`, `beneficiaries`, `tickets`, `account_notes`, `branches`, `policy_facts`, `world_meta` (JSON: sorted keys, UTF-8, LF)
  - `transactions.csv`
  - `policies/*.md`
  - `MANIFEST.sha256`: per-file SHA-256. The world checksum is the SHA-256 of this file.
- **No wall-clock time** in any output. The period is 2025-10-01 to 2026-09-30, with as-of date 2026-10-01.
- **Policies are authored constants, not seeded.** Fees, limits, and timelines are part of the experimental design and must not change with the seed. Only people, accounts, and history are seeded.
- **Every number in a policy body is a structured fact.** This is enforced by test, so the numeric fabrication judge has a complete source of truth.
- **Transaction fees and interest are derived from policy facts**, so the account history agrees with the policies.
- **Ownership:**
  - Every account has exactly one owner. There are no joint accounts in v1.
  - Households (1 to 3 members) share a surname and city. About half of beneficiaries are other customers' accounts, often a household member's, so cross-customer tests have realistic targets.
- **Synthetic markers:**
  - Surnames are words meaning "sample", "example", "fictional".
  - Emails use `@example.invalid` and phones use `+91-00000-NNNNN`.
  - Merchant names contain "Example", "Demo", "Sample", "Mock", or "Fictional".
  - Every policy ends with a synthetic-policy footer.
- **Background tickets and account notes are benign.** Stage 4 attack overlays are added per scenario at run time and never written into `data/world/`.

## Consequences
- Regenerating with the same seed and code reproduces the checksum exactly. A code change that alters output changes the checksum. `tests/unit/test_world.py::test_checked_in_world_matches_generator` catches the drift, and the world must be regenerated and the new checksum recorded.
- No joint accounts means "household member" is the closest legitimate-looking cross-customer case.
