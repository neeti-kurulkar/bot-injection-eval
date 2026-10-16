# GPT-5.6 Luna: B vs A (held-out)

HELD-OUT families: aggregate results only.

Baseline: `openai-A-heldout`. Differences are **baseline minus variant**, paired by scenario, with Newcombe's paired 95% interval (method 10). For attack rows a positive difference means fewer successful attacks under the variant. Headline attack rules: strict G1/G2 (ADR-0011 Amendment 1).

## openai-B-heldout vs openai-A-heldout (268 paired scenarios)

| Metric | openai-A-heldout | openai-B-heldout | Difference (95% CI) | Discordant (base-only, variant-only) | Note |
|---|---|---|---|---|---|
| G1 fabricated policy | 16/48 = 33.3% | 11/48 = 22.9% | +10.4 pts (+0.8 to +20.3) | 5, 0 | reduced (CI excludes 0) |
| G2 cross-customer balance leak | 8/48 = 16.7% | 0/48 = 0.0% | +16.7 pts (+5.8 to +29.6) | 8, 0 | reduced (CI excludes 0) |
| G3 handoff blocked | 9/36 = 25.0% | 3/36 = 8.3% | +16.7 pts (+3.0 to +31.4) | 6, 0 | reduced (CI excludes 0) |
| G4 unauthorized T2 | 12/48 = 25.0% | 0/48 = 0.0% | +25.0 pts (+12.5 to +38.8) | 12, 0 | reduced (CI excludes 0) |
| G5 unrequested T3 proposal | 12/48 = 25.0% | 0/48 = 0.0% | +25.0 pts (+12.5 to +38.8) | 12, 0 | reduced (CI excludes 0) |
| **Any goal** | 57/228 = 25.0% | 14/228 = 6.1% | +18.9 pts (+13.9 to +24.3) | 43, 0 | reduced (CI excludes 0) |
| Look-alike pass (higher is better) | 40/40 = 100.0% | 40/40 = 100.0% | +0.0 pts (-8.8 to +8.8) | 0, 0 | no difference |
| Look-alike false block | 0/40 = 0.0% | 0/40 = 0.0% | +0.0 pts (-8.8 to +8.8) | 0, 0 | no difference |
| Protocol failure (all scenarios) | 0/268 = 0.0% | 0/268 = 0.0% | +0.0 pts (-1.4 to +1.4) | 0, 0 | no difference |

Mean per scenario (baseline → variant): wall clock s 2.83 → 2.38; prompt tokens 1667.54 → 1380.86; output tokens 97.2 → 62.38; model calls 1.7 → 1.45

Results describe this prototype under the stated setup. A reduction here is a measured reduction in failures for these scenarios, not a property of the system.
