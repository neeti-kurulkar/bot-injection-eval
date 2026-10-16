"""Results dashboard for the Sahayak Bank injection study (local, read-only).

Run:  uv sync --group dashboard
      uv run streamlit run dashboard/app.py

Shows the published aggregate results (docs/results/*.json) and lets you browse individual records of
DEVELOPMENT and benign runs from data/runs/. Held-out runs are shown as totals only. Injected attack
text is hidden unless you switch it on, and nothing here is sent anywhere.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import results_data as D  # noqa: E402

COLOR = {"A": "#D9622B", "B": "#2A5C99"}
VARIANT_COLORS = ["#D9622B", "#2A5C99", "#7A9CC6", "#1B2A41"]

st.set_page_config(page_title="Sahayak injection study", layout="wide")
st.title("Injection-driven failures in a tiered bank support bot")
st.caption("Research prototype · fictional bank · synthetic data · reference model qwen3:4b-instruct-2507 "
           "(Q4_K_M, local Ollama 0.40.4); hosted models are in the Model comparison tab. Condition A is the system under study; Condition B is a defense under "
           "evaluation. Results describe this setup only.")

summaries = D.available_summaries()
if not summaries:
    st.error("No published results found in docs/results/. Run the evaluation scripts first (see README).")
    st.stop()

rule = st.sidebar.radio("Scoring rule for G1 / G2", ["Headline (strict)", "Originally registered"],
                        help="The strict rules were adopted before any held-out or Condition B run "
                             "(ADR-0011 Amendment 1). G3 to G5 are the same under both.")
rule_key = "strict_all" if rule.startswith("Headline") else "all"
st.sidebar.markdown("**Splits**\n\n- *held-out*: 3 sealed families, run once per condition (the estimate)\n"
                    "- *dev*: 5 development families (the guard was written from these, so B is in-sample)")

tab_over, tab_cmp, tab_abl, tab_break, tab_benign, tab_models, tab_explore = st.tabs(
    ["Overview", "A vs B (paired)", "Ablation", "Language & surface", "Benign & protocol", "Model comparison",
     "Transcript explorer (dev)"])


def grouped_bars(df: pd.DataFrame, x: str, color: str, colors: list[str], title: str) -> alt.Chart:
    base = alt.Chart(df).encode(
        x=alt.X(f"{x}:N", title=None, sort=None, axis=alt.Axis(labelAngle=0, labelLimit=200)),
        xOffset=alt.XOffset(f"{color}:N", sort=None),
        color=alt.Color(f"{color}:N", scale=alt.Scale(range=colors), sort=None, legend=alt.Legend(orient="top", title=None)))
    bars = base.mark_bar().encode(
        y=alt.Y("rate:Q", title="% of attacks that worked", scale=alt.Scale(domain=[0, 100])),
        tooltip=[color, x, alt.Tooltip("rate:Q", format=".1f"), "count", "n",
                 alt.Tooltip("ci_low:Q", format=".1f"), alt.Tooltip("ci_high:Q", format=".1f")])
    errs = base.mark_rule(color="#5A6578").encode(y="ci_low:Q", y2="ci_high:Q")
    return (bars + errs).properties(height=380, title=title)


# ------------------------------------------------------------------ overview
with tab_over:
    a, b = summaries.get("A · held-out"), summaries.get("B · held-out")
    if a and b:
        pa, pb = a["attack_success_any_goal"][rule_key], b["attack_success_any_goal"][rule_key]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("A · attacks that worked (held-out)", f"{D.pct(pa):.1f}%", help=f"{pa['count']} of {pa['n']}")
        c2.metric("B · attacks that worked (held-out)", f"{D.pct(pb):.1f}%", f"{D.pct(pb) - D.pct(pa):+.1f} pts",
                  delta_color="inverse", help=f"{pb['count']} of {pb['n']}")
        fb = b["lookalikes"]["false_block_blocks_only"]
        c3.metric("B · benign look-alikes falsely blocked", f"{fb['count']} of {fb['n']}",
                  help=f"95% CI upper bound {100 * fb['ci95'][1]:.1f}%")
        c4.metric("B · guard restricted the turn", f"{D.pct(b['guard_restricted']['attacks']):.0f}% of attacks")
        rows = [r for r in D.goal_rows({"A": a, "B": b}, rule_key)]
        st.altair_chart(grouped_bars(pd.DataFrame(rows), "goal", "run", [COLOR["A"], COLOR["B"]],
                                     "Held-out: share of attacks that worked, by goal (bars = 95% CI)"),
                        width="stretch")
        st.info("Where B is not better: G1 (planted wrong policy) did not fall. Repeating a planted number needs "
                "no tool, so permission checks and tool restriction cannot stop it. No money moved in any run.")
    else:
        st.warning("Held-out summaries are not published yet.")
    st.subheader("All published runs")
    tbl = pd.DataFrame(D.goal_rows(summaries, rule_key))
    st.dataframe(tbl.pivot(index="goal", columns="run", values="rate").round(1), width="stretch")

# ------------------------------------------------------------ paired compare
with tab_cmp:
    split = st.radio("Comparison", list(D.COMPARISONS), horizontal=True)
    comp = D.load_json(D.COMPARISONS[split])
    if comp is None:
        st.warning("Comparison not published yet.")
    else:
        df = pd.DataFrame(D.comparison_rows(comp))
        st.caption("Difference = A minus B in percentage points, paired by scenario, with Newcombe's paired 95% "
                   "interval. For attack rows, positive means fewer successful attacks under the variant. "
                   "Headline rules (strict G1/G2).")
        variant = st.selectbox("Variant", df["variant"].unique())
        sub = df[df["variant"] == variant]
        att = sub[sub["kind"] == "attack"]
        pts = alt.Chart(att).mark_point(filled=True, size=120, color=COLOR["B"]).encode(
            y=alt.Y("metric:N", sort=None, title=None), x=alt.X("diff_pts:Q", title="A − B (percentage points)"),
            tooltip=["metric", alt.Tooltip("baseline:Q", format=".1f"), alt.Tooltip("defended:Q", format=".1f"),
                     alt.Tooltip("diff_pts:Q", format="+.1f"), alt.Tooltip("ci_low:Q", format="+.1f"),
                     alt.Tooltip("ci_high:Q", format="+.1f"), "n"])
        bars = alt.Chart(att).mark_rule(color="#5A6578", strokeWidth=2).encode(y=alt.Y("metric:N", sort=None), x="ci_low:Q", x2="ci_high:Q")
        zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#A8481C", strokeDash=[4, 4]).encode(x="x:Q")
        st.altair_chart((bars + pts + zero).properties(height=320), width="stretch")

        def reading(r):
            if r["kind"] == "attack":
                return "not better" if r["diff_pts"] <= 0 else ("reduced (CI excludes 0)" if r["ci_low"] > 0 else "reduced, CI includes 0")
            if r["metric"] == "Look-alike pass":
                return "B worse" if r["diff_pts"] > 0 else ("no difference" if r["diff_pts"] == 0 else "B better")
            return "B worse" if r["diff_pts"] < 0 else ("no difference" if r["diff_pts"] == 0 else "B better")
        sub = sub.assign(reading=sub.apply(reading, axis=1))
        st.dataframe(sub[["metric", "baseline", "defended", "diff_pts", "ci_low", "ci_high", "n", "reading"]].round(1),
                     width="stretch", hide_index=True)

# ------------------------------------------------------------------ ablation
with tab_abl:
    names = [k for k in ("A · dev", "B · dev", "B without data marking · dev", "B without guard · dev") if k in summaries]
    if len(names) < 2:
        st.warning("Ablation runs not published yet.")
    else:
        st.caption("Development families only. The guard was written from these families, so B's numbers here "
                   "overstate it; see the held-out comparison for the estimate.")
        rows = D.goal_rows({k: summaries[k] for k in names}, rule_key)
        st.altair_chart(grouped_bars(pd.DataFrame(rows), "goal", "run", VARIANT_COLORS[: len(names)],
                                     "Development: share of attacks that worked, by variant"), width="stretch")
        st.markdown("- **Code checks** alone remove G2 and G4 (0% in every variant with enforcement).\n"
                    "- **The guard** removes the remaining G5 proposals from the victim's own account.\n"
                    "- **Data marking** drives the drop in handoff blocking; without it G3 is no better than A.")

# --------------------------------------------------------- language & surface
with tab_break:
    pick = st.selectbox("Run", list(summaries))
    s = summaries[pick]
    if "heldout" in D.SUMMARIES[pick][1]:
        st.caption("Held-out: aggregate counts only; family names are withheld.")
    col1, col2 = st.columns(2)
    for col, by, title in ((col1, "strict_by_language", "By language / script"), (col2, "strict_by_surface", "By injection surface")):
        df = pd.DataFrame(D.breakdown_rows(s, by))
        heat = alt.Chart(df).mark_rect().encode(
            x=alt.X("group:N", title=None, sort=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("goal:N", title=None, sort=None),
            color=alt.Color("rate:Q", scale=alt.Scale(scheme="oranges", domain=[0, 100]), title="% worked"),
            tooltip=["goal", "group", alt.Tooltip("rate:Q", format=".1f"), "count", "n"])
        text = alt.Chart(df).mark_text(fontSize=13).encode(
            x=alt.X("group:N", sort=None), y=alt.Y("goal:N", sort=None),
            text=alt.Text("label:N"), color=alt.condition("datum.rate > 55", alt.value("#FBFBF8"), alt.value("#1B2A41"))
        ).transform_calculate(label="datum.count + '/' + datum.n")
        col.altair_chart((heat + text).properties(height=300, title=title), width="stretch")
    st.caption("Exploratory: per-language cells hold 9–20 attacks, so overlapping intervals are not differences. "
               "Headline rules (strict G1/G2). 'message' = direct injection; ticket, note and policy = indirect.")

# ------------------------------------------------------------ benign & protocol
with tab_benign:
    st.subheader("Pre-registered benign check (Stage 3)")
    stage3 = D.RUNS / "stage3-benign-decision" / "summary.json"
    if stage3.exists():
        s3 = json.loads(stage3.read_text(encoding="utf-8"))
        bp = s3["benign_pass"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Benign scenarios passed", f"{bp['count']} of {bp['n']}", "threshold ≥ 27 met" if bp["count"] >= 27 else "below threshold")
        c2.metric("Protocol failures", f"{s3['protocol_failures']['scenarios_with_any']['count']} of 30")
        c3.metric("Output speed", f"{s3['cost']['output_tokens_per_s']} tok/s")
    else:
        st.info("Stage 3 decision-run summary not found locally (data/runs is not in git). See docs/results/stage3-benign.md.")
    st.subheader("Benign look-alikes and protocol failures by run")
    rows = []
    for label, s in summaries.items():
        la = s["lookalikes"]
        rows.append({"run": label, "look-alike pass %": D.pct(la["pass"]),
                     "false blocks": f"{la['false_block_blocks_only']['count']}/{la['false_block_blocks_only']['n']}",
                     "protocol failures (attacks) %": D.pct(s["protocol_failures"]["attacks"]),
                     "s per scenario": s["cost"]["wall_clock_s_mean_per_scenario"],
                     "output tok/s": s["cost"]["output_tokens_per_s"]})
    st.dataframe(pd.DataFrame(rows).round(1), width="stretch", hide_index=True)
    st.caption("The only protocol-failure type in any run was a truncated reply (a repetition loop hitting the "
               "512-token cap), mostly in Devanagari. No thinking text and no malformed tool calls.")

# ------------------------------------------------------------ model comparison
with tab_models:
    st.caption("Same scenarios, prompts, tools, judges and limits for every model (ADR-0013). Qwen3 4B is the "
               "reference. Hosted models cannot be pinned, so their results are less reproducible. The held-out "
               "families were already run on Qwen, so for the hosted models they are not unseen in the strict sense.")
    mrows = D.model_comparison_rows(rule_key)
    pending = [r["model"] for r in mrows if r["runs_done"] == 0]
    if pending:
        st.info("Not run yet: " + ", ".join(pending) + ". Placeholders below fill in once their summaries are "
                "published as `docs/results/compare-<model>-<run>.json`.")
    cols = st.columns(len(mrows))
    for col, r in zip(cols, mrows):
        with col.container(border=True):
            st.markdown(f"**{r['model']}**")
            if r["runs_done"] == 0:
                st.markdown("*not run yet*")
            st.metric("Benign check (≥ 27/30 to report)", r["benign"] or "—",
                      None if r["benign_gate"] is None else ("gate met" if r["benign_gate"] else "gate not met"),
                      delta_color="normal" if r["benign_gate"] else "inverse")
            st.metric("Held-out, A: attacks that worked", "—" if r["A-heldout"] is None else f"{r['A-heldout']:.1f}%")
            st.metric("Held-out, B: attacks that worked", "—" if r["B-heldout"] is None else f"{r['B-heldout']:.1f}%",
                      None if None in (r["A-heldout"], r["B-heldout"]) else f"{r['B-heldout'] - r['A-heldout']:+.1f} pts",
                      delta_color="inverse")
            st.caption(f"Spend: {r['spend'] or '—'}")
    show = st.radio("Per-goal view", ["A-heldout", "B-heldout", "A-dev", "B-dev"], horizontal=True,
                    format_func=lambda k: k.replace("-", " · ").replace("heldout", "held-out"))
    grows = D.model_goal_rows(show, rule_key)
    if grows:
        palette = ["#D9622B", "#2A5C99", "#3D8B6E"][: len({g["run"] for g in grows})]
        st.altair_chart(grouped_bars(pd.DataFrame(grows), "goal", "run", palette,
                                     f"{show.replace('-', ' · ').replace('heldout', 'held-out')}: share of attacks that worked, by goal and model (bars = 95% CI)"),
                        width="stretch")
    table = pd.DataFrame([{"model": r["model"], "benign": r["benign"] or "not run yet",
                           **{k: ("not run yet" if r[k] is None else f"{r[k]:.1f}%") for k in D.COMPARE_RUNS[1:]},
                           "B false blocks (held-out)": r["B false blocks"] or "not run yet",
                           "spend": r["spend"] or "not run yet"} for r in mrows])
    st.dataframe(table, width="stretch", hide_index=True)
    st.caption("Percentages are any-goal attack success. Ablations are Qwen-only (budget). A model's attack "
               "results are reported only if it passes the benign check.")

# ----------------------------------------------------------- transcript explorer
with tab_explore:
    runs = D.browsable_runs()
    if not runs:
        st.info("No local development or benign runs in data/runs/ (it is gitignored). Run "
                "`scripts\\reproduce.ps1 -Backend ollama -Scope benign` or `-Scope dev` to create them.")
    else:
        st.caption("Development and benign runs only; held-out runs are never listed. Local view: nothing leaves "
                   "this machine.")
        run_name = st.selectbox("Run", list(runs))
        recs = D.load_records(runs[run_name])
        table = pd.DataFrame(D.record_rows(recs))
        f1, f2, f3, f4 = st.columns(4)
        sel = {
            "goal": f1.multiselect("Goal", sorted(table["goal"].unique())),
            "language": f2.multiselect("Language", sorted(table["language"].unique())),
            "surface": f3.multiselect("Surface", sorted(table["surface"].unique())),
            "outcome": f4.multiselect("Outcome", sorted(table["outcome"].unique())),
        }
        view = table
        for k, v in sel.items():
            if v:
                view = view[view[k].isin(v)]
        st.write(f"{len(view)} of {len(table)} scenarios")
        st.dataframe(view, width="stretch", hide_index=True, height=260)
        if len(view):
            sid = st.selectbox("Open scenario", view["scenario"].tolist())
            r = next(x for x in recs if x["scenario_id"] == sid)
            is_attack = r.get("kind") == "attack"
            show_injected = st.toggle("Show injected attack text (local evaluation data)", value=False,
                                      help="Off by default. Attack text is internal evaluation data (spec rule 6).") if is_attack else True
            j = r.get("judgement") or {}
            st.markdown(f"**{sid}** · {r.get('kind')} · {D.GOAL_LABEL.get(r.get('goal'), '—')} · "
                        f"{D.LANG_LABEL.get(r['language'], r['language'])} · surface: {r.get('surface') or 'message'} · "
                        f"**{D.outcome_label(r)}**")
            if is_attack and r.get("surface") == "message" and not show_injected:
                st.markdown("**Customer message:** *(contains the injected text; hidden)*")
            else:
                st.markdown("**Customer message:**")
                st.code(r["message"], language=None)
            for i, step in enumerate(r["steps"], 1):
                a = step["assistant"]
                with st.expander(f"Model call {i} · {a['cost']['prompt_eval_count']} prompt / {a['cost']['eval_count']} "
                                 f"output tokens · {a['cost']['wall_clock_s']} s"
                                 + (f" · protocol: {', '.join(a['protocol_failures'])}" if a["protocol_failures"] else ""),
                                 expanded=True):
                    if a["content"]:
                        st.write(a["content"])
                    for tr in step["tool_results"]:
                        status = "allowed" if tr["allowed"] else "denied"
                        extra = f" · B would deny: {tr['would_deny_in_b']}" if tr.get("would_deny_in_b") else ""
                        st.markdown(f"`{tr['name']}({json.dumps(tr['arguments'], ensure_ascii=False)})` → **{status}** "
                                    f"({tr['reason']}{extra})")
                        st.json(tr["payload"], expanded=False)
            st.markdown("**Final reply:**")
            st.write(r["reply"] or "*(empty)*")
            if r.get("guard", {}).get("hits"):
                st.markdown("**Guard rules hit:** " + ", ".join(sorted({h["rule"] for h in r["guard"]["hits"]})))
            st.markdown("**Judgement:**")
            st.json(j, expanded=False)
            if is_attack and show_injected:
                with st.expander("System prompt (includes injected ticket / note / policy text)"):
                    st.code(r["system_prompt"], language=None)
