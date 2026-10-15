"""Scenario runner: one JSONL record per scenario, written as it completes.

Resumable: scenario IDs already in records.jsonl are skipped, so an
interrupted run continues where it stopped. Each scenario runs on a fresh
copy of the template DB. Run metadata (model pin, Ollama version, processor,
git commit, seed) goes to meta.json and is repeated in summary.json.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sahayak.agent.context import ContextBuilder
from sahayak.agent.loop import LLMAgent
from sahayak.config import REPO_ROOT, Settings
from sahayak.domain.models import Condition
from sahayak.eval.judges import NumericPolicyJudge, judge_benign
from sahayak.eval.stats import proportion
from sahayak.mockbank.repo import Repository, copy_db
from sahayak.policy.store import PolicyStore
from sahayak.tools.layer import ToolLayer
from sahayak.tools.session import SessionManager


def git_state() -> dict:
    """HEAD commit plus a git tree hash of the exact working-tree content (tracked and untracked,
    minus .gitignore). If the tree is later committed unchanged, its commit has this same tree."""
    import os

    def git(*a, env=None):
        return subprocess.run(["git", *a], cwd=REPO_ROOT, capture_output=True, text=True, env=env).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        git("add", "-A", env=env)
        tree = git("write-tree", env=env)
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain")),
            "worktree_tree": tree}


def repair_torn_tail(records: Path) -> int:
    """Drop a partial last line left by an interruption. Returns bytes removed."""
    if not records.exists():
        return 0
    data = records.read_bytes()
    if not data or data.endswith(b"\n"):
        return 0
    keep = data.rfind(b"\n") + 1
    records.write_bytes(data[:keep])
    return len(data) - keep


def completed_ids(records: Path) -> set[str]:
    if not records.exists():
        return set()
    ids = set()
    for line in records.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                ids.add(json.loads(line)["scenario_id"])
            except (json.JSONDecodeError, KeyError):
                continue  # a torn last line from an interruption is ignored and re-run
    return ids


def run_scenario(scenario: dict, condition: Condition, backend, settings: Settings, template_db: Path,
                 policies: PolicyStore, numeric: NumericPolicyJudge, tmp_dir: Path) -> dict:
    t0 = time.perf_counter()
    db = copy_db(template_db, tmp_dir / f"{scenario['scenario_id']}.db")
    repo = Repository.open(db)
    try:
        overlay = tuple(scenario.get("overlay", {}).get("policy_docs", ()))
        sessions = SessionManager(repo, seed=scenario["seed"])
        tools = ToolLayer(repo, sessions, policies, policy_overlay=overlay)
        context = ContextBuilder(repo, policies, data_marking=(condition is Condition.B),
                                 seed=scenario["seed"], policy_overlay=overlay)
        agent = LLMAgent(backend.with_seed(scenario["seed"]), tools, context,
                         settings.max_steps, settings.max_output_tokens_per_turn)
        s = sessions.create(condition)
        sessions.authenticate(s.session_id, scenario["customer_id"])
        messages = context.initial_messages(scenario["customer_id"], scenario["message"])
        turn = agent.run_turn(s.session_id, messages)
        audit = repo.list_audit(s.session_id)
        handoffs = repo.list_handoffs(s.session_id)
        approvals = repo.list_approvals(s.session_id)
    finally:
        repo.close()
        db.unlink(missing_ok=True)

    payloads = [tr["payload"] for st in turn.steps for tr in st["tool_results"]]
    num = numeric.judge(turn.reply, payloads)
    judgement = judge_benign(scenario, audit, handoffs, turn.outcome, turn.reply, turn.protocol_failures, num) \
        if scenario["kind"] == "benign" else None
    costs = [st["assistant"]["cost"] for st in turn.steps]
    return {
        "scenario_id": scenario["scenario_id"],
        "condition": condition.value,
        "category": scenario.get("category"),
        "language": scenario["language"],
        "customer_id": scenario["customer_id"],
        "message": scenario["message"],
        "system_prompt": messages[0]["content"],
        "prefetched_policy_docs": context.prefetched,
        "expected_policy_doc": scenario["expected"].get("policy_doc"),
        "reply": turn.reply,
        "outcome": turn.outcome,
        "error": turn.error,
        "protocol_failures": turn.protocol_failures,
        "steps": turn.steps,
        "audit": audit,
        "handoffs": handoffs,
        "approvals": approvals,
        "numeric_judge": {"fabricated": num.fabricated, "ungrounded": num.ungrounded,
                          "claim_sentences": num.claim_sentences},
        "judgement": judgement,
        "cost": {
            "model_calls": len(costs),
            "prompt_tokens": sum(c["prompt_eval_count"] for c in costs),
            "output_tokens": sum(c["eval_count"] for c in costs),
            "eval_duration_ns": sum(c["eval_duration_ns"] for c in costs),
            "prompt_eval_duration_ns": sum(c["prompt_eval_duration_ns"] for c in costs),
            "load_duration_ns": sum(c["load_duration_ns"] for c in costs),
            "retries": sum(c["retries"] for c in costs),
            "wall_clock_s": round(time.perf_counter() - t0, 3),
        },
    }


def run(scenarios: list[dict], condition: Condition, backend, settings: Settings, template_db: Path,
        policies: PolicyStore, facts: list[dict], out_dir: Path, run_id: str, notes: str = "",
        progress=print) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = out_dir / "records.jsonl"
    done = completed_ids(records)
    meta_path = out_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {
        "run_id": run_id, "condition": condition.value, "started_at": datetime.now(timezone.utc).isoformat(),
        "seed": settings.seed, "git": git_state(), "notes": notes, "sessions": []}
    torn = repair_torn_tail(records)
    numeric = NumericPolicyJudge(facts)
    todo = [s for s in scenarios if s["scenario_id"] not in done]
    progress(f"{run_id}: {len(done)} already done, {len(todo)} to run")
    session_log = {"resumed_at": datetime.now(timezone.utc).isoformat(), "skipped": len(done), "ran": 0,
                   "torn_bytes_removed": torn}
    meta["sessions"].append(session_log)
    with tempfile.TemporaryDirectory() as tmp, records.open("a", encoding="utf-8", newline="\n") as f:
        for i, sc in enumerate(todo, 1):
            rec = run_scenario(sc, condition, backend, settings, template_db, policies, numeric, Path(tmp))
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            f.flush()
            session_log["ran"] += 1
            verdict = "" if rec["judgement"] is None else ("PASS" if rec["judgement"]["pass"] else "FAIL")
            progress(f"  [{i}/{len(todo)}] {sc['scenario_id']} {sc['language']:<8} {rec['outcome']:<11} "
                     f"{verdict:<4} {rec['cost']['wall_clock_s']:.1f}s")
            if i == 1:
                meta["model"] = backend.metadata()  # after the first call, so the model is loaded
    meta.setdefault("model", backend.metadata())
    meta["finished_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return records


def load_records(records: Path) -> list[dict]:
    return [json.loads(line) for line in records.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(records: list[dict], meta: dict, threshold_count: int | None = None) -> dict:
    n = len(records)
    judged = [r for r in records if r["judgement"] is not None]
    passes = sum(r["judgement"]["pass"] for r in judged)
    crit_fail = Counter(k for r in judged for k, ok in r["judgement"]["criteria"].items() if not ok)
    pf = Counter(p for r in records for p in r["protocol_failures"])
    by = lambda key: {v: proportion(sum(r["judgement"]["pass"] for r in judged if r[key] == v),  # noqa: E731
                                    sum(1 for r in judged if r[key] == v))
                      for v in sorted({r[key] for r in judged})}
    faq = [r for r in records if r.get("expected_policy_doc")]
    retrieval = defaultdict(lambda: [0, 0])
    for r in faq:
        retrieval[r["language"]][0] += r["expected_policy_doc"] in r["prefetched_policy_docs"]
        retrieval[r["language"]][1] += 1
    out_tok = sum(r["cost"]["output_tokens"] for r in records)
    eval_s = sum(r["cost"]["eval_duration_ns"] for r in records) / 1e9
    prompt_tok = sum(r["cost"]["prompt_tokens"] for r in records)
    prompt_s = sum(r["cost"]["prompt_eval_duration_ns"] for r in records) / 1e9
    wall = sum(r["cost"]["wall_clock_s"] for r in records)
    calls = sum(r["cost"]["model_calls"] for r in records)
    summary = {
        "run_id": meta.get("run_id"),
        "condition": meta.get("condition"),
        "model": meta.get("model"),
        "git": meta.get("git"),
        "seed": meta.get("seed"),
        "scenarios": n,
        "benign_pass": proportion(passes, len(judged)),
        "criteria_failures": dict(crit_fail),
        "protocol_failures": {"scenarios_with_any": proportion(sum(1 for r in records if r["protocol_failures"]), n),
                              "by_type": dict(pf)},
        "outcomes": dict(Counter(r["outcome"] for r in records)),
        "pass_by_language": by("language"),
        "pass_by_category": by("category"),
        "retrieval_hit_by_language": {k: proportion(v[0], v[1]) for k, v in sorted(retrieval.items())},
        "numeric_fabrication": proportion(sum(r["numeric_judge"]["fabricated"] for r in records), n),
        "cost": {
            "wall_clock_s_total": round(wall, 1),
            "wall_clock_s_mean_per_scenario": round(wall / n, 2) if n else None,
            "model_calls_total": calls,
            "model_calls_mean_per_scenario": round(calls / n, 2) if n else None,
            "prompt_tokens_total": prompt_tok,
            "output_tokens_total": out_tok,
            "prompt_tokens_mean_per_scenario": round(prompt_tok / n, 1) if n else None,
            "output_tokens_mean_per_scenario": round(out_tok / n, 1) if n else None,
            "output_tokens_per_s": round(out_tok / eval_s, 1) if eval_s else None,
            "prompt_tokens_per_s": round(prompt_tok / prompt_s, 1) if prompt_s else None,
            "retries": sum(r["cost"]["retries"] for r in records),
        },
    }
    if threshold_count is not None:
        summary["threshold"] = {"required_passes": threshold_count, "of": len(judged),
                                "met": passes >= threshold_count}
    return summary

