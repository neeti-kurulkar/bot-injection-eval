"""Dashboard data layer and app smoke test. The app test is skipped unless the optional
'dashboard' dependency group (Streamlit) is installed."""

from __future__ import annotations

import sys

import pytest

from sahayak.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "dashboard"))
import results_data as D  # noqa: E402

APP = str(REPO_ROOT / "dashboard" / "app.py")


def test_published_summaries_load_with_expected_headline():
    s = D.available_summaries()
    assert {"A · held-out", "B · held-out"} <= set(s)
    any_a = s["A · held-out"]["attack_success_any_goal"]["strict_all"]
    any_b = s["B · held-out"]["attack_success_any_goal"]["strict_all"]
    assert (any_a["count"], any_a["n"], any_b["count"], any_b["n"]) == (63, 228, 31, 228)


def test_goal_rows_cover_every_goal_plus_any():
    rows = D.goal_rows({"A": D.available_summaries()["A · held-out"]})
    assert [r["goal"] for r in rows] == [D.GOAL_LABEL[g] for g in D.GOALS] + ["Any goal"]


def test_heldout_runs_are_never_browsable():
    for name, path in D.browsable_runs().items():
        assert "heldout" not in name
        assert all(r.get("split") != "heldout" for r in D.load_records(path))


def test_heldout_summaries_carry_no_family_names():
    for label, (stem, split) in D.SUMMARIES.items():
        s = D.load_json(stem)
        if s and split == "heldout":
            assert isinstance(s["attack_success_any_goal"]["by_family"], str)


@pytest.fixture(scope="module")
def app():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(APP, default_timeout=180).run()


def test_app_runs_without_exceptions(app):
    assert not app.exception
    labels = {m.label: m.value for m in app.metric}
    assert labels["A · attacks that worked (held-out)"] == "27.6%"
    assert labels["B · attacks that worked (held-out)"] == "13.6%"


def test_injected_text_hidden_by_default(app):
    if "stage5-A-dev" not in D.browsable_runs():
        pytest.skip("local dev run records not present")
    explorer_run = [s for s in app.selectbox if s.label == "Run"][-1]
    explorer_run.set_value("stage5-A-dev").run()
    surface = next(m for m in app.multiselect if m.label == "Surface")
    surface.set_value(["message"]).run()
    kind_rows = D.record_rows(D.load_records(D.browsable_runs()["stage5-A-dev"]))
    first_message_attack = next(r["scenario"] for r in kind_rows if r["kind"] == "attack" and r["surface"] == "message")
    next(s for s in app.selectbox if s.label == "Open scenario").set_value(first_message_attack).run()
    text = " ".join(m.value for m in app.markdown)
    assert "contains the injected text; hidden" in text
    rec = next(r for r in D.load_records(D.browsable_runs()["stage5-A-dev"]) if r["scenario_id"] == first_message_attack)
    assert rec["message"] not in " ".join(c.value for c in app.code)


def test_model_comparison_has_qwen_and_placeholders():
    rows = {r["slug"]: r for r in D.model_comparison_rows()}
    assert set(rows) == set(D.MODELS)
    q = rows["qwen3-4b"]
    assert q["benign"] == "29/30" and q["A-heldout"] is not None and q["B-heldout"] is not None
    for slug in ("sarvam-105b", "gpt-5.6-luna"):  # until compare-<slug>-*.json is published
        if not any(D.load_json(f"compare-{slug}-{run}") for run in D.COMPARE_RUNS):
            assert rows[slug]["runs_done"] == 0 and rows[slug]["B-heldout"] is None
