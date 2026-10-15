"""Runner smoke tests on the stub backend: records, resumability, summary. No model needed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sahayak.agent.backend import StubBackend
from sahayak.config import Settings, load_settings
from sahayak.domain.models import Condition
from sahayak.eval.judges import load_facts
from sahayak.eval.runner import completed_ids, load_records, run, summarize
from sahayak.generate.benign import SET_NAME, build_benign, load_scenarios, scenarios_bytes
from sahayak.mockbank.repo import build_template_db
from sahayak.policy.store import PolicyStore

S = load_settings()
WORLD = S.world_dir


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    if not (WORLD / "MANIFEST.sha256").exists():
        pytest.skip("world not generated")
    db = tmp_path_factory.mktemp("db") / "sahayak.db"
    build_template_db(WORLD, db)
    return db, PolicyStore.from_dir(WORLD / "policies"), load_facts(WORLD)


def smart_stub():
    """Calls the expected tool once, then answers, so benign judging can pass."""
    def script(messages, i):
        if i == 0:
            user = messages[-1]["content"]
            if "balance" in user.lower():
                acct = messages[0]["content"].split("Accounts: ")[1].split(" ")[0]
                return {"content": "", "tool_calls": [{"function": {"name": "get_balance",
                                                                    "arguments": {"account_id": acct}}}]}
        return {"content": "Done."}
    return StubBackend(script)


def test_frozen_benign_set_matches_generator_and_checksum():
    tickets = S.data_dir / "tickets"
    pinned = (tickets / f"{SET_NAME}.sha256").read_text().split()[0]
    scenarios = load_scenarios(tickets / f"{SET_NAME}.json", expected_sha256=pinned)
    assert scenarios_bytes(build_benign(WORLD, S.seed)) == (tickets / f"{SET_NAME}.json").read_bytes()
    assert len(scenarios) == 30 and len({s["scenario_id"] for s in scenarios}) == 30


def test_benign_required_ids_belong_to_the_customer():
    accounts = {a["account_id"]: a["customer_id"] for a in json.loads((WORLD / "accounts.json").read_text("utf-8"))}
    tickets = {t["ticket_id"]: t["customer_id"] for t in json.loads((WORLD / "tickets.json").read_text("utf-8"))}
    for s in build_benign(WORLD, S.seed):
        for req in s["expected"]["required"]:
            for k, v in req["args"].items():
                owner = accounts.get(v) if k == "account_id" else tickets.get(v)
                assert owner == s["customer_id"], s["scenario_id"]


def test_run_is_resumable_and_skips_done(env, tmp_path):
    db, policies, facts = env
    scenarios = build_benign(WORLD, S.seed)[:6]
    out = tmp_path / "run"
    run(scenarios[:2], Condition.A, smart_stub(), S, db, policies, facts, out, "t", progress=lambda *_: None)
    assert completed_ids(out / "records.jsonl") == {"BEN-001", "BEN-002"}
    # simulate an interruption that left a torn line
    with (out / "records.jsonl").open("a", encoding="utf-8") as f:
        f.write('{"scenario_id": "BEN-003", "trunc')
    run(scenarios, Condition.A, smart_stub(), S, db, policies, facts, out, "t", progress=lambda *_: None)
    recs = [json.loads(line) for line in (out / "records.jsonl").read_text("utf-8").splitlines()
            if line.strip().endswith("}")]
    ids = [r["scenario_id"] for r in recs]
    assert sorted(ids) == [s["scenario_id"] for s in scenarios] and len(ids) == len(set(ids))
    meta = json.loads((out / "meta.json").read_text("utf-8"))
    assert [x["ran"] for x in meta["sessions"]] == [2, 4]


def test_records_contain_audit_costs_and_judgement(env, tmp_path):
    db, policies, facts = env
    sc = [s for s in build_benign(WORLD, S.seed) if s["category"] == "balance"][:1]
    out = tmp_path / "run2"
    run(sc, Condition.A, smart_stub(), S, db, policies, facts, out, "t2", progress=lambda *_: None)
    rec = load_records(out / "records.jsonl")[0]
    assert rec["judgement"]["pass"], rec["judgement"]
    assert rec["audit"][0]["tool"] == "get_balance" and rec["cost"]["model_calls"] == 2
    summary = summarize([rec], json.loads((out / "meta.json").read_text("utf-8")))
    assert summary["benign_pass"]["count"] == 1 and summary["cost"]["output_tokens_per_s"] > 0
