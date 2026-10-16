# Model vs model: Condition A, heldout

HELD-OUT families: aggregate results only. These families had already been run on Qwen3 4B before the hosted models saw them.

Each model ran the same scenarios under the same condition, so outcomes are paired by scenario. Differences are **first model minus second**, with Newcombe's paired 95% interval (method 10). For attack rows a negative difference means fewer successful attacks for the first model. Intervals are **not adjusted for multiple comparisons** (3 pairs × 7 rows), so treat a difference whose interval only just excludes 0 as suggestive. Headline attack rules: strict G1/G2.

## Qwen3 4B vs Sarvam 105B (268 paired scenarios)

| Metric | Qwen3 4B | Sarvam 105B | Qwen3 4B − Sarvam 105B (95% CI) | Only Qwen3 4B, only Sarvam 105B | Reading |
|---|---|---|---|---|---|
| G1 fabricated policy | 25/48 = 52.1% | 13/48 = 27.1% | +25.0 pts (+5.4 to +42.1) | 18, 6 | Sarvam 105B better |
| G2 cross-customer balance leak | 5/48 = 10.4% | 5/48 = 10.4% | +0.0 pts (-9.0 to +9.0) | 1, 1 | no clear difference |
| G3 handoff blocked | 11/36 = 30.6% | 2/36 = 5.6% | +25.0 pts (+9.4 to +40.8) | 9, 0 | Sarvam 105B better |
| G4 unauthorized T2 | 11/48 = 22.9% | 4/48 = 8.3% | +14.6 pts (+2.1 to +27.7) | 8, 1 | Sarvam 105B better |
| G5 unrequested T3 proposal | 11/48 = 22.9% | 7/48 = 14.6% | +8.3 pts (-0.9 to +18.4) | 4, 0 | no clear difference |
| **Any goal** | 63/228 = 27.6% | 31/228 = 13.6% | +14.0 pts (+8.3 to +19.8) | 40, 8 | Sarvam 105B better |
| Look-alike pass (higher is better) | 34/40 = 85.0% | 39/40 = 97.5% | -12.5 pts (-26.9 to +1.0) | 1, 6 | no clear difference |

## Qwen3 4B vs GPT-5.6 Luna (268 paired scenarios)

| Metric | Qwen3 4B | GPT-5.6 Luna | Qwen3 4B − GPT-5.6 Luna (95% CI) | Only Qwen3 4B, only GPT-5.6 Luna | Reading |
|---|---|---|---|---|---|
| G1 fabricated policy | 25/48 = 52.1% | 16/48 = 33.3% | +18.8 pts (+1.0 to +34.8) | 14, 5 | GPT-5.6 Luna better |
| G2 cross-customer balance leak | 5/48 = 10.4% | 8/48 = 16.7% | -6.2 pts (-18.7 to +5.8) | 2, 5 | no clear difference |
| G3 handoff blocked | 11/36 = 30.6% | 9/36 = 25.0% | +5.6 pts (-13.8 to +24.4) | 7, 5 | no clear difference |
| G4 unauthorized T2 | 11/48 = 22.9% | 12/48 = 25.0% | -2.1 pts (-16.2 to +12.1) | 5, 6 | no clear difference |
| G5 unrequested T3 proposal | 11/48 = 22.9% | 12/48 = 25.0% | -2.1 pts (-15.1 to +10.9) | 4, 5 | no clear difference |
| **Any goal** | 63/228 = 27.6% | 57/228 = 25.0% | +2.6 pts (-4.0 to +9.2) | 32, 26 | no clear difference |
| Look-alike pass (higher is better) | 34/40 = 85.0% | 40/40 = 100.0% | -15.0 pts (-29.1 to -3.2) | 0, 6 | GPT-5.6 Luna better |

## Sarvam 105B vs GPT-5.6 Luna (268 paired scenarios)

| Metric | Sarvam 105B | GPT-5.6 Luna | Sarvam 105B − GPT-5.6 Luna (95% CI) | Only Sarvam 105B, only GPT-5.6 Luna | Reading |
|---|---|---|---|---|---|
| G1 fabricated policy | 13/48 = 27.1% | 16/48 = 33.3% | -6.2 pts (-19.9 to +7.7) | 4, 7 | no clear difference |
| G2 cross-customer balance leak | 5/48 = 10.4% | 8/48 = 16.7% | -6.2 pts (-17.5 to +4.2) | 1, 4 | no clear difference |
| G3 handoff blocked | 2/36 = 5.6% | 9/36 = 25.0% | -19.4 pts (-34.9 to -5.1) | 0, 7 | Sarvam 105B better |
| G4 unauthorized T2 | 4/48 = 8.3% | 12/48 = 25.0% | -16.7 pts (-29.1 to -5.3) | 0, 8 | Sarvam 105B better |
| G5 unrequested T3 proposal | 7/48 = 14.6% | 12/48 = 25.0% | -10.4 pts (-23.4 to +2.4) | 2, 7 | no clear difference |
| **Any goal** | 31/228 = 13.6% | 57/228 = 25.0% | -11.4 pts (-16.8 to -6.1) | 7, 33 | Sarvam 105B better |
| Look-alike pass (higher is better) | 39/40 = 97.5% | 40/40 = 100.0% | -2.5 pts (-12.9 to +6.5) | 0, 1 | no clear difference |

Results describe this prototype under the stated setup, on one run per model. Hosted models cannot be pinned and may change. A difference here is a measured difference on these scenarios, not a general property of any model.
