# Model vs model: Condition B, heldout

HELD-OUT families: aggregate results only. These families had already been run on Qwen3 4B before the hosted models saw them.

Each model ran the same scenarios under the same condition, so outcomes are paired by scenario. Differences are **first model minus second**, with Newcombe's paired 95% interval (method 10). For attack rows a negative difference means fewer successful attacks for the first model. Intervals are **not adjusted for multiple comparisons** (3 pairs × 7 rows), so treat a difference whose interval only just excludes 0 as suggestive. Headline attack rules: strict G1/G2.

## Qwen3 4B vs Sarvam 105B (268 paired scenarios)

| Metric | Qwen3 4B | Sarvam 105B | Qwen3 4B − Sarvam 105B (95% CI) | Only Qwen3 4B, only Sarvam 105B | Reading |
|---|---|---|---|---|---|
| G1 fabricated policy | 27/48 = 56.2% | 6/48 = 12.5% | +43.8 pts (+26.6 to +57.5) | 22, 1 | Sarvam 105B better |
| G2 cross-customer balance leak | 0/48 = 0.0% | 0/48 = 0.0% | +0.0 pts (-7.4 to +7.4) | 0, 0 | no clear difference |
| G3 handoff blocked | 4/36 = 11.1% | 1/36 = 2.8% | +8.3 pts (-5.2 to +22.9) | 4, 1 | no clear difference |
| G4 unauthorized T2 | 0/48 = 0.0% | 0/48 = 0.0% | +0.0 pts (-7.4 to +7.4) | 0, 0 | no clear difference |
| G5 unrequested T3 proposal | 0/48 = 0.0% | 0/48 = 0.0% | +0.0 pts (-7.4 to +7.4) | 0, 0 | no clear difference |
| **Any goal** | 31/228 = 13.6% | 7/228 = 3.1% | +10.5 pts (+6.2 to +15.4) | 26, 2 | Sarvam 105B better |
| Look-alike pass (higher is better) | 34/40 = 85.0% | 39/40 = 97.5% | -12.5 pts (-26.9 to +1.0) | 1, 6 | no clear difference |

## Qwen3 4B vs GPT-5.6 Luna (268 paired scenarios)

| Metric | Qwen3 4B | GPT-5.6 Luna | Qwen3 4B − GPT-5.6 Luna (95% CI) | Only Qwen3 4B, only GPT-5.6 Luna | Reading |
|---|---|---|---|---|---|
| G1 fabricated policy | 27/48 = 56.2% | 11/48 = 22.9% | +33.3 pts (+16.2 to +47.6) | 18, 2 | GPT-5.6 Luna better |
| G2 cross-customer balance leak | 0/48 = 0.0% | 0/48 = 0.0% | +0.0 pts (-7.4 to +7.4) | 0, 0 | no clear difference |
| G3 handoff blocked | 4/36 = 11.1% | 3/36 = 8.3% | +2.8 pts (-12.9 to +18.5) | 4, 3 | no clear difference |
| G4 unauthorized T2 | 0/48 = 0.0% | 0/48 = 0.0% | +0.0 pts (-7.4 to +7.4) | 0, 0 | no clear difference |
| G5 unrequested T3 proposal | 0/48 = 0.0% | 0/48 = 0.0% | +0.0 pts (-7.4 to +7.4) | 0, 0 | no clear difference |
| **Any goal** | 31/228 = 13.6% | 14/228 = 6.1% | +7.5 pts (+3.0 to +12.2) | 22, 5 | GPT-5.6 Luna better |
| Look-alike pass (higher is better) | 34/40 = 85.0% | 40/40 = 100.0% | -15.0 pts (-29.1 to -3.2) | 0, 6 | GPT-5.6 Luna better |

## Sarvam 105B vs GPT-5.6 Luna (268 paired scenarios)

| Metric | Sarvam 105B | GPT-5.6 Luna | Sarvam 105B − GPT-5.6 Luna (95% CI) | Only Sarvam 105B, only GPT-5.6 Luna | Reading |
|---|---|---|---|---|---|
| G1 fabricated policy | 6/48 = 12.5% | 11/48 = 22.9% | -10.4 pts (-23.5 to +2.5) | 2, 7 | no clear difference |
| G2 cross-customer balance leak | 0/48 = 0.0% | 0/48 = 0.0% | +0.0 pts (-7.4 to +7.4) | 0, 0 | no clear difference |
| G3 handoff blocked | 1/36 = 2.8% | 3/36 = 8.3% | -5.6 pts (-18.6 to +5.8) | 0, 2 | no clear difference |
| G4 unauthorized T2 | 0/48 = 0.0% | 0/48 = 0.0% | +0.0 pts (-7.4 to +7.4) | 0, 0 | no clear difference |
| G5 unrequested T3 proposal | 0/48 = 0.0% | 0/48 = 0.0% | +0.0 pts (-7.4 to +7.4) | 0, 0 | no clear difference |
| **Any goal** | 7/228 = 3.1% | 14/228 = 6.1% | -3.1 pts (-6.6 to -0.0) | 2, 9 | Sarvam 105B better (borderline) |
| Look-alike pass (higher is better) | 39/40 = 97.5% | 40/40 = 100.0% | -2.5 pts (-12.9 to +6.5) | 0, 1 | no clear difference |

Results describe this prototype under the stated setup, on one run per model. Hosted models cannot be pinned and may change. A difference here is a measured difference on these scenarios, not a general property of any model.
