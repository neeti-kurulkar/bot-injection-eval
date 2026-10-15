# Stage 4 Attack Suite: Statistics

Split manifest `data/splits/attack_split_v1.json`, SHA-256 `bfb052761180bc00dea856266b6c1d5b2d658cb582ef32c56ff9250e2c9c4d14`. Every file listed in it was verified by `python -m sahayak.cli attack-stats`. Held-out content is reported **as counts only**.

## Counts

| | Development | Held-out |
|---|---|---|
| Families | 5 | 3 (HF-1..3, opaque) |
| Attack items | 380 | 228 |
| Benign look-alikes | 40 (10 templates × 4) | 40 (10 templates × 4) |

| Goal | Dev | Held-out |
|---|---|---|
| G1 fabricated policy | 80 | 48 |
| G2 cross-customer leakage | 80 | 48 |
| G3 handoff blocking | 60 | 36 |
| G4 unauthorized T2 | 80 | 48 |
| G5 unauthorized T3 | 80 | 48 |

| Surface | Dev | Held-out |
|---|---|---|
| Current message | 80 | 48 |
| Prior ticket | 100 | 60 |
| Account note | 100 | 60 |
| Policy document | 100 | 60 |

| Language | Dev attacks | Held-out attacks | Dev look-alikes | Held-out look-alikes |
|---|---|---|---|---|
| English | 95 | 57 | 10 | 10 |
| Hinglish | 95 | 57 | 10 | 10 |
| Devanagari Hindi | 95 | 57 | 10 | 10 |
| Romanized Hindi | 95 | 57 | 10 | 10 |

Development items per family: 76 each (delimiter_spoof, fake_system_notice, obfuscated_instruction, policy_spoof, urgency_pressure). Held-out items per family: 76 each.

## Policy-surface exposure (pre-run, retrieval only)

These numbers say whether the poisoned policy document lands in the bot's top-2 prefetched policy excerpts for its trigger question. They were computed during the pre-freeze validation and count only whether a document was retrieved; no content was read.

| Language | Dev | Held-out |
|---|---|---|
| English | 23/25 | 14/15 |
| Hinglish | 24/25 | 15/15 |
| Devanagari Hindi | 25/25 | 15/15 |
| Romanized Hindi | 25/25 | 15/15 |

Unexposed policy-surface scenarios still run. They count as attack failures in the all-scenario denominator and are excluded from the exposed-only rate (ADR-0011).

## Validation before freezing (all 688 items, aggregate only)
- No unfilled placeholders.
- Every planted G1 value is flagged by the numeric judge.
- G4 and G5 targets belong to the intended owner: the victim for third-party surfaces, the household member for the message surface.
- G5 destinations belong to an outsider.
- Look-alike required resources belong to the session customer.
- **Problems found: none.**

## Human language review
`data/attacks/dev/review_sample.md` holds 16 **development** items, 4 per language, from 3 different families plus one look-alike each. They need a human check of the Hinglish and Hindi wording (spec Stage 4). Held-out items cannot be reviewed without unsealing. If the review finds systematic language problems, the procedure in ADR-0011 applies.
