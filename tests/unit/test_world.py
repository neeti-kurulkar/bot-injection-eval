"""Stage 1: synthetic world determinism and invariants. No model needed."""

from __future__ import annotations

import collections
import csv
import io
import json
import re
from pathlib import Path

import pytest

from sahayak.config import load_settings
from sahayak.generate import names
from sahayak.generate.policy_corpus import DOCS, fact_value, render_doc
from sahayak.generate.world import (
    N_MONTHS,
    generate_world,
    verify_world,
    world_files,
    write_world,
)

SEED = load_settings().seed
DIGIT = re.compile(r"[0-9०-९]")


@pytest.fixture(scope="module")
def files() -> dict[str, bytes]:
    return world_files(generate_world(SEED))


def _json(files, name):
    return json.loads(files[name].decode("utf-8"))


def _txns(files):
    return list(csv.DictReader(io.StringIO(files["transactions.csv"].decode("utf-8"))))


# ---------------------------------------------------------------- determinism
def test_two_runs_same_seed_are_byte_identical(tmp_path: Path):
    c1, h1 = write_world(SEED, tmp_path / "a")
    c2, h2 = write_world(SEED, tmp_path / "b")
    assert h1 == h2 and c1 == c2
    paths_a = sorted(p.relative_to(tmp_path / "a") for p in (tmp_path / "a").rglob("*") if p.is_file())
    paths_b = sorted(p.relative_to(tmp_path / "b") for p in (tmp_path / "b").rglob("*") if p.is_file())
    assert paths_a == paths_b
    for rel in paths_a:
        assert (tmp_path / "a" / rel).read_bytes() == (tmp_path / "b" / rel).read_bytes(), rel


def test_different_seed_changes_people(files):
    other = world_files(generate_world(SEED + 1))
    assert other["customers.json"] != files["customers.json"]
    assert other["policy_facts.json"] == files["policy_facts.json"]  # policies are seed-independent


def test_checked_in_world_matches_generator(files):
    world_dir = load_settings().world_dir
    if not (world_dir / "MANIFEST.sha256").exists():
        pytest.skip("world not generated yet")
    ok, _, problems = verify_world(world_dir)
    assert ok, problems
    for rel, data in files.items():
        assert (world_dir / rel).read_bytes() == data, f"{rel} differs from generator output"


def test_lf_line_endings_only(files):
    for rel, data in files.items():
        assert b"\r\n" not in data, rel


# ------------------------------------------------------------------- counts
def test_required_counts(files):
    assert len(_json(files, "customers.json")) == 200
    assert len(_json(files, "accounts.json")) == 300
    assert sum(1 for p in files if p.startswith("policies/")) == 40


def test_twelve_months_about_twenty_per_month(files):
    per = collections.Counter((t["account_id"], t["ts"][:7]) for t in _txns(files))
    months = collections.Counter(a for a, _ in per)
    assert len(months) == 300 and all(n == N_MONTHS for n in months.values())
    mean = sum(per.values()) / len(per)
    assert 18 <= mean <= 23, mean


# ---------------------------------------------------------------- ownership
def test_every_account_has_exactly_one_existing_owner(files):
    customers = {c["customer_id"] for c in _json(files, "customers.json")}
    accounts = _json(files, "accounts.json")
    ids = [a["account_id"] for a in accounts]
    assert len(ids) == len(set(ids))
    assert all(isinstance(a["customer_id"], str) and a["customer_id"] in customers for a in accounts)
    assert {a["customer_id"] for a in accounts} == customers  # nobody without an account


def test_households_with_multiple_members_exist(files):
    sizes = collections.Counter(c["household_id"] for c in _json(files, "customers.json"))
    assert sum(1 for n in sizes.values() if n > 1) >= 20


def test_cards_and_beneficiaries_reference_real_records(files):
    accounts = {a["account_id"] for a in _json(files, "accounts.json")}
    customers = {c["customer_id"] for c in _json(files, "customers.json")}
    assert all(c["account_id"] in accounts for c in _json(files, "cards.json"))
    for b in _json(files, "beneficiaries.json"):
        assert b["customer_id"] in customers
        assert b["account_ref"] in accounts or b["account_ref"].startswith("EXT-")
    owner = {a["account_id"]: a["customer_id"] for a in _json(files, "accounts.json")}
    for b in _json(files, "beneficiaries.json"):
        assert owner.get(b["account_ref"]) != b["customer_id"]


def test_balances_reconcile_and_never_go_negative(files):
    bal = {a["account_id"]: a["opening_balance_paise"] for a in _json(files, "accounts.json")}
    for t in _txns(files):
        if t["status"] != "posted":
            continue
        amt = int(t["amount_paise"])
        bal[t["account_id"]] += amt if t["direction"] == "credit" else -amt
        assert bal[t["account_id"]] >= 0, t["txn_id"]
    for a in _json(files, "accounts.json"):
        assert bal[a["account_id"]] == a["balance_paise"], a["account_id"]


def test_fee_transactions_use_policy_values(files):
    allowed = {fact_value(k) * 100 for k in ("atm_fee_beyond_free", "sms_alert_fee_quarterly",
                                              "debit_card_annual_fee_classic", "debit_card_annual_fee_platinum")}
    fees = [int(t["amount_paise"]) for t in _txns(files) if t["txn_type"] == "fee"]
    assert fees and set(fees) <= allowed


# ------------------------------------------------------------ synthetic marks
def test_people_are_obviously_synthetic(files):
    for c in _json(files, "customers.json"):
        assert c["display_name"].split()[-1] in names.SURNAMES
        assert c["email"].endswith("@example.invalid")
        assert c["phone"].startswith("+91-00000-")


# ------------------------------------------------------------------ policies
def _body(text: str) -> str:
    return text.split("---\n", 2)[2]


def test_policy_fact_keys_unique_and_categories_covered():
    keys = [f.key for d in DOCS for f in d.facts]
    assert len(keys) == len(set(keys))
    cats = {d.category for d in DOCS}
    assert {"fees", "refunds", "disputes", "cards", "grievance"} <= cats


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.doc_id)
def test_every_number_in_a_policy_body_is_a_fact(doc):
    text, facts = render_doc(doc)
    body = _body(text)
    assert "{" not in body and "}" not in body
    for f in facts:
        assert f["rendered"] in body, f"{f['key']} not used in {doc.doc_id}"
    stripped = body
    for r in sorted((f["rendered"] for f in facts), key=len, reverse=True):
        stripped = stripped.replace(r, "")
    assert not DIGIT.search(stripped), f"untracked number in {doc.doc_id}: {DIGIT.findall(stripped)}"


def test_policy_facts_file_matches_corpus(files):
    facts = _json(files, "policy_facts.json")
    assert len(facts) == sum(len(d.facts) for d in DOCS)
    assert all(f["fact_id"] == f"{f['doc_id']}.{f['key']}" for f in facts)
