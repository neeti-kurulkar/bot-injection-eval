# ADR-0012: Condition B guard and ablation variants

Status: Proposed (Stage 6 gate)

## Decision

**Variants** (`src/sahayak/eval/runner.py: VARIANTS`). They differ only in three switches:

| Variant | ToolLayer tier + ownership enforcement | Data marking | Guard |
|---|---|---|---|
| A (baseline) | off | off | none |
| **B (defended)** | on | on | rules |
| B-nomark (ablation) | on | off | rules |
| B-noguard (ablation) | on | on | none |

Same model, prompt base, decoding, limits, and scenarios in every variant. No second model is loaded: the guard is pure regular expressions, enforced by a test that allows only `re`, `unicodedata`, `dataclasses`, and `typing` imports.

**What the guard screens:** all untrusted text placed in the turn's context. That is the customer message, the recent ticket bodies, the account notes, and the prefetched policy excerpts (`ContextBuilder.untrusted`). Policy text that arrives later through a `search_policy` tool result is not screened; data marking covers that path.

**What a guard hit does:** the turn runs *restricted*. Only `search_policy`, `get_branch_hours`, and `request_human_handoff` are offered, and the ToolLayer denies anything else with `guard_restricted`. The reply is never blocked and handoff always works (ADR-0008).

**Rules** (`src/sahayak/guard/rules.py`). Each rule cites the development families that motivated it, and a test checks that only development families are cited:

| Rule | Targets | Evidence (dev) |
|---|---|---|
| R1 | Zero-width / bidi characters; Latin and Cyrillic mixed in one word | obfuscated_instruction |
| R2 | Fake data delimiters, role tags, end-of-text markers | delimiter_spoof |
| R3 | System / configuration notice styling, "audit mode" | fake_system_notice |
| R4 | "Policy Pnn (revised …)" claims in untrusted text | policy_spoof |
| R5 | Internal tool names in untrusted text | fake_system_notice, delimiter_spoof |
| R6 | Instructions not to connect a human (four language variants) | urgency_pressure, delimiter_spoof, obfuscated_instruction, fake_system_notice |
| R7 | OTP "not needed / no time / already verified" | delimiter_spoof, urgency_pressure, policy_spoof, obfuscated_instruction |
| R8 | A transfer between two account IDs requested in text | all five development families (G5) |
| R9 | "Also include / append the balance" instructions | fake_system_notice, policy_spoof, obfuscated_instruction |

**Offline check, before any B run** (deterministic, no model):
- 353/380 development attacks flagged. urgency_pressure is caught least (49/76), because emotional pleas carry no technical marker.
- 0/40 development look-alikes, 0/30 benign scenarios, 0/150 background tickets, 0/100 notes, and 0/91 policy chunks flagged.

**This is in-sample:** the rules were written from these same families. The development-run numbers therefore overstate the guard. The held-out run (sealed families) is the estimate.

## Consequences
- The guard is expected to help most against G2, G4, and G5, where restriction removes the tools.
- It is expected to help least against G1 and G3: restriction does not stop the model repeating a planted number or skipping a handoff. Those depend on data marking.
- False blocks are measured on look-alikes as required calls denied under restriction.
