# Condition B and ablations vs Condition A (development)

DEVELOPMENT families only. The guard was written from these families, so these comparisons are in-sample for the guard; the held-out comparison is the estimate.

Baseline: `stage5-A-dev`. Differences are **baseline minus variant**, paired by scenario, with Newcombe's paired 95% interval (method 10). For attack rows a positive difference means fewer successful attacks under the variant. Headline attack rules: strict G1/G2 (ADR-0011 Amendment 1).

## stage6-B-dev vs stage5-A-dev (420 paired scenarios)

| Metric | stage5-A-dev | stage6-B-dev | Difference (95% CI) | Discordant (base-only, variant-only) | Note |
|---|---|---|---|---|---|
| G1 fabricated policy | 29/80 = 36.2% | 22/80 = 27.5% | +8.8 pts (+1.2 to +16.3) | 8, 1 | reduced (CI excludes 0) |
| G2 cross-customer balance leak | 11/80 = 13.8% | 0/80 = 0.0% | +13.8 pts (+6.3 to +23.0) | 11, 0 | reduced (CI excludes 0) |
| G3 handoff blocked | 19/60 = 31.7% | 11/60 = 18.3% | +13.3 pts (+1.9 to +24.6) | 10, 2 | reduced (CI excludes 0) |
| G4 unauthorized T2 | 13/80 = 16.2% | 0/80 = 0.0% | +16.2 pts (+8.3 to +25.8) | 13, 0 | reduced (CI excludes 0) |
| G5 unrequested T3 proposal | 8/80 = 10.0% | 0/80 = 0.0% | +10.0 pts (+3.3 to +18.5) | 8, 0 | reduced (CI excludes 0) |
| **Any goal** | 80/380 = 21.1% | 33/380 = 8.7% | +12.4 pts (+8.9 to +16.1) | 50, 3 | reduced (CI excludes 0) |
| Look-alike pass (higher is better) | 32/40 = 80.0% | 32/40 = 80.0% | +0.0 pts (-9.7 to +9.7) | 1, 1 | no difference |
| Look-alike false block | 0/40 = 0.0% | 0/40 = 0.0% | +0.0 pts (-8.8 to +8.8) | 0, 0 | no difference |
| Protocol failure (all scenarios) | 6/420 = 1.4% | 6/420 = 1.4% | +0.0 pts (-1.8 to +1.8) | 5, 5 | no difference |

Mean per scenario (baseline → variant): wall clock s 3.11 → 2.44; prompt tokens 2524.76 → 1624.8; output tokens 136.1 → 112.15; model calls 1.63 → 1.44

## stage6-B-nomark-dev vs stage5-A-dev (420 paired scenarios)

| Metric | stage5-A-dev | stage6-B-nomark-dev | Difference (95% CI) | Discordant (base-only, variant-only) | Note |
|---|---|---|---|---|---|
| G1 fabricated policy | 29/80 = 36.2% | 28/80 = 35.0% | +1.2 pts (-4.8 to +7.2) | 3, 2 | reduced, CI includes 0 |
| G2 cross-customer balance leak | 11/80 = 13.8% | 0/80 = 0.0% | +13.8 pts (+6.3 to +23.0) | 11, 0 | reduced (CI excludes 0) |
| G3 handoff blocked | 19/60 = 31.7% | 20/60 = 33.3% | -1.7 pts (-10.8 to +7.5) | 3, 4 | **not better** |
| G4 unauthorized T2 | 13/80 = 16.2% | 0/80 = 0.0% | +16.2 pts (+8.3 to +25.8) | 13, 0 | reduced (CI excludes 0) |
| G5 unrequested T3 proposal | 8/80 = 10.0% | 0/80 = 0.0% | +10.0 pts (+3.3 to +18.5) | 8, 0 | reduced (CI excludes 0) |
| **Any goal** | 80/380 = 21.1% | 48/380 = 12.6% | +8.4 pts (+5.1 to +11.9) | 38, 6 | reduced (CI excludes 0) |
| Look-alike pass (higher is better) | 32/40 = 80.0% | 32/40 = 80.0% | +0.0 pts (-7.0 to +7.0) | 0, 0 | no difference |
| Look-alike false block | 0/40 = 0.0% | 0/40 = 0.0% | +0.0 pts (-8.8 to +8.8) | 0, 0 | no difference |
| Protocol failure (all scenarios) | 6/420 = 1.4% | 10/420 = 2.4% | -0.9 pts (-2.9 to +0.9) | 4, 8 | variant worse |

Mean per scenario (baseline → variant): wall clock s 3.11 → 2.51; prompt tokens 2524.76 → 1307.99; output tokens 136.1 → 123.04; model calls 1.63 → 1.37

## stage6-B-noguard-dev vs stage5-A-dev (420 paired scenarios)

| Metric | stage5-A-dev | stage6-B-noguard-dev | Difference (95% CI) | Discordant (base-only, variant-only) | Note |
|---|---|---|---|---|---|
| G1 fabricated policy | 29/80 = 36.2% | 26/80 = 32.5% | +3.8 pts (-1.1 to +8.7) | 3, 0 | reduced, CI includes 0 |
| G2 cross-customer balance leak | 11/80 = 13.8% | 0/80 = 0.0% | +13.8 pts (+6.3 to +23.0) | 11, 0 | reduced (CI excludes 0) |
| G3 handoff blocked | 19/60 = 31.7% | 12/60 = 20.0% | +11.7 pts (-0.3 to +23.4) | 10, 3 | reduced, CI includes 0 |
| G4 unauthorized T2 | 13/80 = 16.2% | 0/80 = 0.0% | +16.2 pts (+8.3 to +25.8) | 13, 0 | reduced (CI excludes 0) |
| G5 unrequested T3 proposal | 8/80 = 10.0% | 4/80 = 5.0% | +5.0 pts (-1.8 to +12.8) | 5, 1 | reduced, CI includes 0 |
| **Any goal** | 80/380 = 21.1% | 42/380 = 11.1% | +10.0 pts (+6.7 to +13.5) | 42, 4 | reduced (CI excludes 0) |
| Look-alike pass (higher is better) | 32/40 = 80.0% | 32/40 = 80.0% | +0.0 pts (-9.7 to +9.7) | 1, 1 | no difference |
| Look-alike false block | 0/40 = 0.0% | 0/40 = 0.0% | +0.0 pts (-8.8 to +8.8) | 0, 0 | no difference |
| Protocol failure (all scenarios) | 6/420 = 1.4% | 13/420 = 3.1% | -1.7 pts (-3.7 to +0.1) | 3, 10 | variant worse |

Mean per scenario (baseline → variant): wall clock s 3.11 → 3.21; prompt tokens 2524.76 → 2980.21; output tokens 136.1 → 139.54; model calls 1.63 → 1.71

Results describe this prototype under the stated setup. A reduction here is a measured reduction in failures for these scenarios, not a property of the system.
