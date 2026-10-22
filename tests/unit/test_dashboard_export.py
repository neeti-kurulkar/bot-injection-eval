"""The public dashboard's data file (web/src/data/study.json) must match the published results and stay
aggregate-only. Regenerate it with: uv run python scripts/export_dashboard_data.py"""

from __future__ import annotations

import importlib.util
import json

from sahayak.config import REPO_ROOT

DATA = REPO_ROOT / "web" / "src" / "data" / "study.json"


def _export_module():
    spec = importlib.util.spec_from_file_location("export_dashboard_data", REPO_ROOT / "scripts" / "export_dashboard_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dashboard_data_is_current(tmp_path, monkeypatch):
    mod = _export_module()
    monkeypatch.setattr(mod, "OUT", tmp_path / "study.json")
    mod.main()
    assert json.loads((tmp_path / "study.json").read_text(encoding="utf-8")) == json.loads(DATA.read_text(encoding="utf-8")), \
        "web/src/data/study.json is stale: run scripts/export_dashboard_data.py"


def test_dashboard_data_headline_matches_reports():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    rows = {(r["model"], r["cond"]): (r["count"], r["n"]) for r in d["overall"]["strict_all|heldout"]}
    assert rows[("Qwen3 4B", "A")] == (63, 228) and rows[("Qwen3 4B", "B")] == (31, 228)
    assert rows[("Sarvam 105B", "B")] == (7, 228) and rows[("GPT-5.6 Luna", "A")] == (57, 228)


def test_dashboard_data_is_aggregate_only():
    text = DATA.read_text(encoding="utf-8")
    for forbidden in ('"message"', '"reply"', '"system_prompt"', '"scenario_id"', "by_family"):
        assert forbidden not in text
