"""Tests for the Action Centre, FAQ and Latest Data Check. Run from repo root: python -m pytest tests -q"""
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import knowledge_content as kc  # noqa: E402
import latest_check as lc  # noqa: E402


def test_real_csv_has_required_columns():
    cols = set(pd.read_csv(ROOT / "data/processed/latest_forecast.csv", nrows=0).columns)
    assert lc.REQUIRED <= cols


def test_json_parses():
    m = json.loads((ROOT / "data/processed/persistence_metrics.json").read_text())
    assert "coverage_by_level" in m and "empirical_coverage" in m


def test_load_latest_real_data():
    d = lc.load_latest(ROOT)
    assert d["dir"] is not None and len(d["latest"]) == 4
    assert d["problems"] == []
    h = lc.data_health(d["latest"], d["history"])
    assert len(h) == 4 and h["days_with_value"].notna().all()


def test_coverage_for_level():
    m = json.loads((ROOT / "data/processed/persistence_metrics.json").read_text())
    assert lc.coverage_for_level(m, 100.0)[0] == "[90.0, inf)"
    assert lc.coverage_for_level(m, 10.0)[0] == "[0.0, 30.0)"


def test_missing_outputs_handled(tmp_path):
    d = lc.load_latest(tmp_path)
    assert d["dir"] is None


def test_bad_json_and_missing_history_reported(tmp_path):
    dst = tmp_path / "data/processed"
    dst.mkdir(parents=True)
    shutil.copy(ROOT / "data/processed/latest_forecast.csv", dst)
    (dst / "persistence_metrics.json").write_text("{not json")
    d = lc.load_latest(tmp_path)
    text = " ".join(d["problems"])
    assert "not valid JSON" in text and "daily_history.csv not found" in text


def test_wrong_columns_reported(tmp_path):
    dst = tmp_path / "data/processed"
    dst.mkdir(parents=True)
    (dst / "latest_forecast.csv").write_text("a,b\n1,2\n")
    d = lc.load_latest(tmp_path)
    assert d["dir"] is None and "missing expected columns" in d["problems"][0]


def test_faq_covers_required_topics_and_search():
    cats = " ".join(kc.faq_categories()).lower()
    for t in ("aqi", "seasonal", "prioritisation", "persistence", "uncertainty", "sensor",
              "responses", "freshness", "coverage", "machine learning"):
        assert t in cats, t
    assert kc.search_faq("sensor")
    assert kc.search_faq("zzzzqqq") == []
    assert all(i["category"] == "Uncertainty" for i in kc.search_faq("", ["Uncertainty"]))


def test_actions_cover_every_tier_and_have_fields():
    for t in kc.TIERS:
        assert kc.actions_for_tier(t), t
    for a in kc.ACTIONS:
        assert {"name", "tiers", "trigger", "response", "rationale", "stakeholder", "refs", "limits"} <= set(a)
        assert all(r in kc.REFERENCES for r in a["refs"])


def test_no_forbidden_claims():
    blob = json.dumps([kc.ACTIONS, kc.FAQ]).lower()
    assert "97%" not in blob and "confirmed source" not in blob


def test_app_runs_without_exception():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "src/app_standalone.py"), default_timeout=60).run()
    assert not at.exception, at.exception
    assert len(at.tabs) >= 3
    # exercise station selectors and FAQ search
    at.selectbox(key="ac_station").select_index(1).run()
    assert not at.exception
    at.selectbox(key="lc_station").select_index(2).run()
    assert not at.exception
    at.text_input(key="kh_query").set_value("sensor").run()
    assert not at.exception
