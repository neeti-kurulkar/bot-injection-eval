"""Human-readable summaries and transcripts for run records."""

from __future__ import annotations

import json

from sahayak.eval.stats import fmt


def summary_markdown(s: dict, title: str) -> str:
    m = s.get("model") or {}
    c = s["cost"]
    lines = [
        f"# {title}",
        "",
        f"Run `{s['run_id']}`, condition {s['condition']}, {s['scenarios']} scenarios. "
        f"Commit `{(s.get('git') or {}).get('commit', '?')[:10]}`"
        f"{' (dirty tree)' if (s.get('git') or {}).get('dirty') else ''}, seed {s.get('seed')}.",
        "",
        "## Model and environment",
        "",
        f"- Model: `{m.get('model_tag')}`, digest `{m.get('model_digest')}`"
        f" (matches pin: {m.get('digest_matches_pin')}), quantization {m.get('quantization')}",
        f"- Ollama {m.get('ollama_version')}, num_ctx {m.get('num_ctx')}, temperature {m.get('temperature')}, "
        f"num_predict {m.get('num_predict')}, processor: {m.get('processor')}",
        f"- Thinking: {m.get('thinking')}",
        "",
        "## Pre-registered benign threshold (ADR-0006)",
        "",
        f"- Benign pass: {fmt(s['benign_pass'])}",
    ]
    if "threshold" in s:
        t = s["threshold"]
        lines.append(f"- Threshold: at least {t['required_passes']}/{t['of']}. **{'MET' if t['met'] else 'NOT MET'}**")
    lines += [
        f"- Failed criteria (scenario counts): {json.dumps(s['criteria_failures']) if s['criteria_failures'] else 'none'}",
        f"- Outcomes: {json.dumps(s['outcomes'])}",
        "",
        "## Protocol failures",
        "",
        f"- Scenarios with any: {fmt(s['protocol_failures']['scenarios_with_any'])}",
        f"- By type: {json.dumps(s['protocol_failures']['by_type']) if s['protocol_failures']['by_type'] else 'none'}",
        f"- Numeric policy fabrication (deterministic judge): {fmt(s['numeric_fabrication'])}",
        "",
    ]
    if "faq_expected_fact" in s:
        f = s["faq_expected_fact"]
        lines += [
            "## FAQ expected-fact presence (descriptive, not a pass criterion)",
            "",
            f"- Replies stating the expected policy number(s): {fmt(f['overall'])}",
            *[f"- {k}: {fmt(v)}" for k, v in f["by_language"].items()],
            f"- Missing: {json.dumps(f['missing']) if f['missing'] else 'none'}",
            "- Presence is not correctness: a reply can contain the number and still state the rule wrongly.",
            "",
        ]
    lines += [
        "## Breakdowns (exploratory, small cells)",
        "",
        "| Language | Pass |", "|---|---|",
        *[f"| {k} | {fmt(v)} |" for k, v in s["pass_by_language"].items()],
        "",
        "| Category | Pass |", "|---|---|",
        *[f"| {k} | {fmt(v)} |" for k, v in s["pass_by_category"].items()],
        "",
        "| Language | Policy retrieval hit (FAQ, top-2 prefetch) |", "|---|---|",
        *[f"| {k} | {fmt(v)} |" for k, v in s["retrieval_hit_by_language"].items()],
        "",
        "## Cost and timing",
        "",
        f"- Wall clock: {c['wall_clock_s_total']} s total, {c['wall_clock_s_mean_per_scenario']} s per scenario",
        f"- Model calls: {c['model_calls_total']} total, {c['model_calls_mean_per_scenario']} per scenario",
        f"- Tokens: {c['prompt_tokens_total']} prompt ({c['prompt_tokens_mean_per_scenario']} per scenario), "
        f"{c['output_tokens_total']} output ({c['output_tokens_mean_per_scenario']} per scenario)",
        f"- Throughput (Ollama fields): {c['output_tokens_per_s']} output tok/s, {c['prompt_tokens_per_s']} prompt tok/s",
        f"- Retries: {c['retries']}",
        "",
    ]
    return "\n".join(lines)


def transcript(r: dict, show_system: bool = True) -> str:
    out = [f"=== {r['scenario_id']} | condition {r['condition']} | {r['category']} | {r['language']} | "
           f"customer {r['customer_id']}"]
    if show_system:
        out += ["--- system prompt", r["system_prompt"]]
    out += ["--- customer", r["message"]]
    for i, st in enumerate(r["steps"], 1):
        a = st["assistant"]
        calls = ", ".join(f"{c['name']}({json.dumps(c['arguments'], ensure_ascii=False)})" for c in a["tool_calls"])
        out.append(f"--- model call {i} ({a['cost']['prompt_eval_count']} prompt / {a['cost']['eval_count']} output tokens, "
                   f"{a['cost']['wall_clock_s']} s){' PROTOCOL: ' + ','.join(a['protocol_failures']) if a['protocol_failures'] else ''}")
        if a["content"]:
            out.append(f"assistant: {a['content']}")
        if calls:
            out.append(f"tool calls: {calls}")
        for tr in st["tool_results"]:
            flag = "allowed" if tr["allowed"] else "denied"
            wd = f", B would deny: {tr['would_deny_in_b']}" if tr["would_deny_in_b"] else ""
            out.append(f"  -> {tr['name']}: {flag} ({tr['reason']}{wd}) {json.dumps(tr['payload'], ensure_ascii=False)[:300]}")
    out.append(f"--- final reply ({r['outcome']})")
    out.append(r["reply"])
    if r["judgement"]:
        j = r["judgement"]
        out.append(f"--- judgement: {'PASS' if j['pass'] else 'FAIL'} {json.dumps(j['criteria'])}")
    if r["numeric_judge"]["ungrounded"]:
        out.append(f"--- ungrounded numbers: {json.dumps(r['numeric_judge']['ungrounded'], ensure_ascii=False)}")
    return "\n".join(out)
