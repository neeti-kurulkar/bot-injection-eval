"""Exports the published, aggregate results to web/src/data/study.json for the public dashboard.

Only docs/results/*.json is read (aggregate summaries). No attack text, no per-scenario records, and no
held-out family names leave this script.

Run: uv run python scripts/export_dashboard_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))
import results_data as D  # noqa: E402

OUT = REPO / "web" / "src" / "data" / "study.json"
RULES = ("strict_all", "all")
METRICS = ("ANY", *D.GOALS)


def r1(x):
    return None if x is None else round(x, 1)


def cell(row: dict) -> dict:
    return {"count": row["count"], "n": row["n"], "rate": r1(row["rate"]), "lo": r1(row["ci_low"]), "hi": r1(row["ci_high"])}


def overall() -> dict:
    """Headline rates use the published intervals verbatim, so they match the reports to the decimal."""
    out = {}
    for rule in RULES:
        for split in D.SPLITS:
            rows = []
            for slug in D.MODELS:
                for cond in "AB":
                    p = D.model_summary(slug, f"{cond}-{split}")["attack_success_any_goal"][rule]
                    rows.append({"model": D.MODEL_SHORT[slug], "cond": cond, "count": p["count"], "n": p["n"],
                                 "rate": r1(100 * p["count"] / p["n"]), "lo": r1(100 * p["ci95"][0]),
                                 "hi": r1(100 * p["ci95"][1])})
            out[f"{rule}|{split}"] = rows
    return out


def by_goal() -> dict:
    out = {}
    for rule in RULES:
        for split in D.SPLITS:
            for cond in "AB":
                out[f"{rule}|{split}|{cond}"] = [{"model": r["model"], "goal": r["goal"], **cell(r)}
                                                 for r in D.model_goal_rows(cond, split, rule)]
    return out


def by_language() -> dict:
    out = {}
    pools = {"both": ("dev", "heldout"), "heldout": ("heldout",), "dev": ("dev",)}
    for rule in RULES:
        for pool, splits in pools.items():
            for cond in "AB":
                for metric in METRICS:
                    out[f"{rule}|{pool}|{cond}|{metric}"] = [{"model": r["model"], "language": r["language"], **cell(r)}
                                                             for r in D.language_rows(metric, cond, splits, rule)]
    return out


def by_surface() -> dict:
    out = {}
    for rule in RULES:
        for split in D.SPLITS:
            for cond in "AB":
                for slug in D.MODELS:
                    out[f"{rule}|{split}|{cond}|{D.MODEL_SHORT[slug]}"] = [
                        {"goal": r["goal"], "surface": r["surface"], **cell(r)} for r in D.surface_rows(slug, cond, split, rule)]
    return out


def paired() -> dict:
    out = {}
    for split in D.SPLITS:
        for slug in D.MODELS:
            out[f"{split}|{D.MODEL_SHORT[slug]}"] = [
                {"key": r["key"], "metric": r["metric"], "a": r["A_count"], "b": r["B_count"], "diff": r1(r["diff_pts"]),
                 "lo": r1(r["ci_low"]), "hi": r1(r["ci_high"]), "fixed": r["a_only"], "broke": r["b_only"],
                 "kind": r["kind"], "reading": D.reading(r)} for r in D.paired_rows(slug, split)]
    return out


def head_to_head() -> dict:
    out = {}
    for split in D.SPLITS:
        for cond in "AB":
            for metric in D.H2H_METRICS:
                out[f"{split}|{cond}|{metric}"] = [
                    {"pair": r["Pair"], "x": r["x"], "y": r["y"], "first": r["First model"], "second": r["Second model"],
                     "diff": r1(r["diff_pts"]), "lo": r1(r["ci_low"]), "hi": r1(r["ci_high"]),
                     "onlyFirst": r["Only first"], "onlySecond": r["Only second"], "verdict": r["Verdict"]}
                    for r in D.head_to_head_rows(cond, split, metric)]
    return out


def models() -> list[dict]:
    out = []
    for slug in D.MODELS:
        ben = D.model_summary(slug, "benign")["benign_pass"]
        runs = {k: D.model_summary(slug, k) for k in ("A-heldout", "B-heldout", "A-dev", "B-dev")}
        out.append({
            "slug": slug, "name": D.MODEL_SHORT[slug],
            "where": "Local, 4-bit, via Ollama" if slug == "qwen3-4b" else "Hosted API",
            "benign": {"count": ben["count"], "n": ben["n"]},
            "benignByLanguage": {D.LANG_LABEL[k]: v["count"] / v["n"] * 100
                                 for k, v in D.model_summary(slug, "benign")["pass_by_language"].items()},
            "lookalikes": {k: runs[k]["lookalikes"]["pass"]["count"] for k in runs},
            "falseBlocksB": runs["B-heldout"]["lookalikes"]["false_block_blocks_only"]["count"],
            "protocol": {k: runs[k]["protocol_failures"]["attacks"]["count"] for k in runs},
            "secondsPerScenario": {k: runs[k]["cost"]["wall_clock_s_mean_per_scenario"] for k in runs},
            "guardRestricted": {k: r1(100 * runs[k]["guard_restricted"]["attacks"]["rate"]) for k in ("B-heldout", "B-dev")},
            "spend": D.SPEND[slug],
        })
    return out


def ablation() -> list[dict]:
    s = D.available_summaries()
    names = ["A · dev", "B · dev", "B without data marking · dev", "B without guard · dev"]
    rows = D.goal_rows({k: s[k] for k in names}, "strict_all")
    label = {"A · dev": "A", "B · dev": "B", "B without data marking · dev": "B without data marking",
             "B without guard · dev": "B without guard"}
    return [{"variant": label[r["run"]], "goal": r["goal"], **cell(r)} for r in rows]


def facts() -> dict:
    comp = D.load_json("facts-vs-B-dev")
    out = {"variants": []}
    for key, name in (("facts-B-facts-dev", "B + fact tool"), ("facts-B-facts-check-dev", "B + fact tool + output check")):
        rows = comp[key]["rows"]
        out["variants"].append({
            "name": name,
            "g1": {"b": rows["G1_fabricated_policy"]["base"]["count"], "v": rows["G1_fabricated_policy"]["variant"]["count"],
                   "n": rows["G1_fabricated_policy"]["n"]},
            "any": {"b": rows["ANY"]["base"]["count"], "v": rows["ANY"]["variant"]["count"], "n": rows["ANY"]["n"],
                    "diff": r1(100 * rows["ANY"]["diff"]), "lo": r1(100 * rows["ANY"]["ci95"][0]),
                    "hi": r1(100 * rows["ANY"]["ci95"][1]), "fixed": rows["ANY"]["discordant"][0],
                    "broke": rows["ANY"]["discordant"][1]},
            "lookalikes": {"b": rows["LOOKALIKE_PASS"]["base"]["count"], "v": rows["LOOKALIKE_PASS"]["variant"]["count"]},
            "calls": comp[key]["cost"]["model_calls"],
        })
    # From the run records, summarised in docs/results/structured-facts.md (not re-derivable from summaries).
    out["details"] = {"toolUsedB_facts": 38, "toolUsedCheck": 93, "scenarios": 420, "correctValue": {"B": 54, "facts": 56, "check": 69},
                      "g1Flagged": 34, "g1Fallback": 4, "cardMisfires": 18, "cardTriggered": 28}
    return out


def main() -> None:
    q_any = {r["model"] + r["condition"][0]: r for r in D.model_any_rows("heldout")}
    data = {
        "generated": "from docs/results (aggregate summaries only)",
        "models": models(),
        "overall": overall(),
        "byGoal": by_goal(),
        "byLanguage": by_language(),
        "bySurface": by_surface(),
        "paired": paired(),
        "headToHead": head_to_head(),
        "ablation": ablation(),
        "facts": facts(),
        "goals": [{"key": g, "label": D.GOAL_LABEL[g], "plain": D.GOAL_PLAIN[g]} for g in D.GOALS],
        "languages": [D.LANG_LABEL[x] for x in D.LANGS],
        "surfaces": [D.SURFACE_LABEL[x] for x in D.SURFACES],
        "judgeCheck": {"hostedVerdicts": 121, "hostedCorrect": 121, "numericFlags": 66, "numericCorrect": 34},
        "headline": {m: r1(q_any[m]["rate"]) for m in q_any},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
