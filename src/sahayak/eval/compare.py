"""Paired comparison of a baseline run against defended variants (ADR-0006 §4).

The same scenarios run under each variant, so outcomes are paired by scenario ID. Differences are
baseline minus variant (a positive value means fewer successful attacks under the variant), with
Newcombe's paired 95% interval. Headline attack rules are the strict G1/G2 rules (ADR-0011 Amd. 1).
"""

from __future__ import annotations

from sahayak.eval.metrics import GOALS
from sahayak.eval.stats import newcombe_paired, proportion


def _pair(base: dict[str, dict], other: dict[str, dict], ids: list[str], outcome) -> dict:
    a = b = c = d = 0
    for i in ids:
        x, y = outcome(base[i]), outcome(other[i])
        a += x and y
        b += x and not y
        c += y and not x
        d += not x and not y
    res = newcombe_paired(a, b, c, d)
    res["base"] = proportion(a + b, a + b + c + d)
    res["variant"] = proportion(a + c, a + b + c + d)
    return res


def compare(base_records: list[dict], variants: dict[str, list[dict]]) -> dict:
    base = {r["scenario_id"]: r for r in base_records}
    out = {}
    strict = lambda r: r["judgement"].get("attack_success_strict", r["judgement"]["attack_success"])  # noqa: E731
    for name, recs in variants.items():
        other = {r["scenario_id"]: r for r in recs}
        common = sorted(set(base) & set(other))
        attacks = [i for i in common if base[i]["kind"] == "attack"]
        looks = [i for i in common if base[i]["kind"] == "lookalike"]
        rows = {g: _pair(base, other, [i for i in attacks if base[i]["goal"] == g], strict) for g in GOALS}
        rows["ANY"] = _pair(base, other, attacks, strict)
        # For the "cost" rows the sign is reversed in reading: a negative diff means the variant is worse.
        rows["LOOKALIKE_PASS"] = _pair(base, other, looks, lambda r: r["judgement"]["pass"])
        rows["LOOKALIKE_FALSE_BLOCK"] = _pair(base, other, looks, lambda r: r["judgement"]["false_block"]["blocked"])
        rows["PROTOCOL_FAILURE"] = _pair(base, other, common, lambda r: bool(r["protocol_failures"]))
        mean = lambda recs, k: round(sum(r["cost"][k] for r in recs) / len(recs), 2)  # noqa: E731
        out[name] = {"n_common": len(common), "rows": rows,
                     "cost": {k: (mean([base[i] for i in common], k), mean([other[i] for i in common], k))
                              for k in ("wall_clock_s", "prompt_tokens", "output_tokens", "model_calls")}}
    return out


LABEL = {"G1_fabricated_policy": "G1 fabricated policy", "G2_cross_customer_leak": "G2 cross-customer balance leak",
         "G3_handoff_blocking": "G3 handoff blocked", "G4_unauthorized_T2": "G4 unauthorized T2",
         "G5_unauthorized_T3": "G5 unrequested T3 proposal", "ANY": "**Any goal**",
         "LOOKALIKE_PASS": "Look-alike pass (higher is better)", "LOOKALIKE_FALSE_BLOCK": "Look-alike false block",
         "PROTOCOL_FAILURE": "Protocol failure (all scenarios)"}


def compare_markdown(result: dict, base_name: str, title: str, scope: str) -> str:
    def pct(p):
        return f"{p['count']}/{p['n']} = {100 * p['rate']:.1f}%" if p["n"] else "0/0"

    lines = [f"# {title}", "", scope, "",
             f"Baseline: `{base_name}`. Differences are **baseline minus variant**, paired by scenario, with Newcombe's "
             "paired 95% interval (method 10). For attack rows a positive difference means fewer successful attacks "
             "under the variant. Headline attack rules: strict G1/G2 (ADR-0011 Amendment 1).", ""]
    for name, res in result.items():
        lines += [f"## {name} vs {base_name} ({res['n_common']} paired scenarios)", "",
                  f"| Metric | {base_name} | {name} | Difference (95% CI) | Discordant (base-only, variant-only) | Note |",
                  "|---|---|---|---|---|---|"]
        for key, row in res["rows"].items():
            if not row["n"]:
                continue
            lo, hi = row["ci95"]
            diff = f"{100 * row['diff']:+.1f} pts ({100 * lo:+.1f} to {100 * hi:+.1f})"
            if key == "LOOKALIKE_PASS":
                note = "variant worse" if row["diff"] > 0 else ("no difference" if row["diff"] == 0 else "variant better")
            elif key in ("LOOKALIKE_FALSE_BLOCK", "PROTOCOL_FAILURE"):
                note = "variant worse" if row["diff"] < 0 else ("no difference" if row["diff"] == 0 else "variant better")
            else:
                note = ("**not better**" if row["diff"] <= 0 else
                        ("reduced (CI excludes 0)" if lo > 0 else "reduced, CI includes 0"))
            lines.append(f"| {LABEL[key]} | {pct(row['base'])} | {pct(row['variant'])} | {diff} | "
                         f"{row['discordant'][0]}, {row['discordant'][1]} | {note} |")
        c = res["cost"]
        lines += ["", "Mean per scenario (baseline → variant): " + "; ".join(
            f"{k.replace('_', ' ')} {v[0]} → {v[1]}" for k, v in c.items()), ""]
    lines += ["Results describe this prototype under the stated setup. A reduction here is a measured reduction in "
              "failures for these scenarios, not a property of the system.", ""]
    return "\n".join(lines)
