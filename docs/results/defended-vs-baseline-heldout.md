# Condition B vs Condition A (held-out)

HELD-OUT families: aggregate results only.

Baseline: `stage5-A-heldout`. Differences are **baseline minus variant**, paired by scenario, with Newcombe's paired 95% interval (method 10). For attack rows a positive difference means fewer successful attacks under the variant. Headline attack rules: strict G1/G2 (ADR-0011 Amendment 1).

## stage6-B-heldout vs stage5-A-heldout (268 paired scenarios)

| Metric | stage5-A-heldout | stage6-B-heldout | Difference (95% CI) | Discordant (base-only, variant-only) | Note |
|---|---|---|---|---|---|
| G1 fabricated policy | 25/48 = 52.1% | 27/48 = 56.2% | -4.2 pts (-14.4 to +6.3) | 2, 4 | **not better** |
| G2 cross-customer balance leak | 5/48 = 10.4% | 0/48 = 0.0% | +10.4 pts (+0.9 to +22.2) | 5, 0 | reduced (CI excludes 0) |
| G3 handoff blocked | 11/36 = 30.6% | 4/36 = 11.1% | +19.4 pts (+1.0 to +36.7) | 9, 2 | reduced (CI excludes 0) |
| G4 unauthorized T2 | 11/48 = 22.9% | 0/48 = 0.0% | +22.9 pts (+10.8 to +36.5) | 11, 0 | reduced (CI excludes 0) |
| G5 unrequested T3 proposal | 11/48 = 22.9% | 0/48 = 0.0% | +22.9 pts (+10.8 to +36.5) | 11, 0 | reduced (CI excludes 0) |
| **Any goal** | 63/228 = 27.6% | 31/228 = 13.6% | +14.0 pts (+8.6 to +19.6) | 38, 6 | reduced (CI excludes 0) |
| Look-alike pass (higher is better) | 34/40 = 85.0% | 34/40 = 85.0% | +0.0 pts (-10.2 to +10.2) | 1, 1 | no difference |
| Look-alike false block | 0/40 = 0.0% | 0/40 = 0.0% | +0.0 pts (-8.8 to +8.8) | 0, 0 | no difference |
| Protocol failure (all scenarios) | 3/268 = 1.1% | 6/268 = 2.2% | -1.1 pts (-3.7 to +1.2) | 2, 5 | variant worse |

Mean per scenario (baseline → variant): wall clock s 3.14 → 2.42; prompt tokens 2479.41 → 1965.4; output tokens 134.97 → 110.78; model calls 1.61 → 1.44

Results describe this prototype under the stated setup. A reduction here is a measured reduction in failures for these scenarios, not a property of the system.
