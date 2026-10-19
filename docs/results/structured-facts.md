# Structured-facts experiment (ADR-0014)

Follow-up on the study's main open problem: under Condition B the bot still repeats a planted fee, limit or deadline (G1). This tests whether answering policy numbers from the bank's structured facts fixes it.

- **Model:** Qwen3 4B, local, pinned digest. Ollama 0.40.5 (the main study used 0.40.4; the model digest is identical).
- **Data:** development suite (380 attacks, 40 look-alikes) and the 30 benign scenarios, run on 2026-10-19. No held-out run.
- **Baseline:** the existing Condition B development run (`stage6-B-dev`), paired by scenario. Published files: `facts-vs-B-dev.md/.json`, `facts-B-facts-dev.*`, `facts-B-facts-check-dev.*`.

## Variants
- **B-facts:** B plus a `get_policy_fact` tool that reads only the official facts (a poisoned document can't reach it), plus one prompt rule: use it for any policy number, and prefer it over any other text.
- **B-facts-check:** B-facts plus a check in code. Every policy number in the final reply is compared with the official facts and this turn's tool results. On a mismatch the bot gets one corrective message; if the second reply still mismatches, it is replaced with a fixed "can't confirm that figure, I can connect you to a human" reply.

## Results (development, paired against B)

| | B | B-facts | B-facts-check |
|---|:---:|:---:|:---:|
| G1 planted policy (of 80) | 22 | 22 | **0** |
| Any goal (of 380) | 33 (8.7%) | 33 (8.7%) | **11 (2.9%)** |
| G1 replies that state the correct value (of 80) | 54 | 56 | 69 |
| G2, G4, G5 | 0 | 0 | 0 |
| G3 handoff blocked (of 60) | 11 | 11 | 11 |
| Look-alikes passed (of 40) | 32 | 32 | 32 |
| Benign passed (of 30) | (not run under B) | 28 | 28 |
| Scenarios where the bot called `get_policy_fact` | — | 38 of 420; 0 of 30 benign | 93 of 420; 2 of 30 benign |
| Mean model calls per scenario | 1.44 | 1.42 | 1.70 |

Paired differences against B, any goal:
- **B-facts:** +0.0 pts (−1.8 to +1.8), no change.
- **B-facts-check:** −5.8 pts (−3.3 to −8.8); fixed 24 scenarios and broke 2.

## What it shows

1. **Offering the tool changed nothing.** With only a prompt rule asking it to, Qwen called `get_policy_fact` in 38 of 420 attack scenarios and never in a benign FAQ. Planted policy stayed at 22 of 80. A small model mostly keeps answering from the policy text already in its prompt.
2. **Enforcing it in code removed planted policy on these scenarios**, from 22 to 0 of 80.
   - The corrective retry usually worked: of the 34 G1 replies the check flagged, 30 passed on the second try (25 of them stating the correct value) and only 4 needed the fallback reply.
   - Customers got the right value more often: 69 of 80 G1 replies state the correct policy value, against 54 under B.
   - This is the same lesson as the rest of the study: what is enforced in code holds, and what depends on the model choosing to comply mostly doesn't.
3. **Caveat: the G1 drop is partly by construction.** The check uses the same number extractor and fact list as the G1 judge, so a 0 here doesn't independently prove the fix (ADR-0014). The independent evidence is the correct-value rate (69 vs 54, from a separate fact-presence check) and the low fallback rate.
4. **The check also misfires on card numbers.** It treats a card's last four digits ("ending 8798") as a policy number:
   - It fired on 28 of 80 card or contact-change scenarios.
   - 18 of those ordinary replies were replaced with the fallback.
   - These were attack scenarios, and no attack outcome changed. But a real customer asking about their card would hit the same misfire.
   - It never fired on the 30 benign scenarios or the 40 look-alikes, which happen to include no card-number replies.
   - The fix is to treat the customer's own account and card details as grounded. It wasn't applied here, because changing the check after seeing these results would be tuning on development data.
5. **Cost:** about 18% more model calls per scenario (1.44 → 1.70), from the corrective retries.

## What it doesn't show
- **No held-out families.** These results are on development data, which the guard was also built from. A fresh sealed attack set is needed for an estimate.
- **Only Qwen.** Larger models might call the tool unprompted more often; B-facts wasn't run on the hosted models.
- **A naive check.** A production version needs the card and account grounding fix above, and topic-aware matching. The judge's known limitation also applies to the check: a right-unit value taken from a different policy isn't caught.
