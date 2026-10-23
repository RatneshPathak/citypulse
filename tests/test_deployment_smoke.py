"""
CityPulse: Mumbai — Deployment Smoke Test
Verifies end-to-end deployability for Streamlit Community Cloud and Hugging Face Spaces:
- Presence and valid parsing of all committed datasets and artifacts
- Secret resolution fallback without exceptions
- All core chart generation and figure object integrity
- Reusable UI component output and required attribution strings
- Syntactic validity of app entry points (app.py and streamlit_app.py)
"""
import json
from pathlib import Path
import py_compile
import unittest

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import config
from config import EVENT_NAME, TEAM_MEMBERS, DATA_ATTRIBUTION, DISCLAIMER_TEXT, get_secret
import charts
import components
import theme
from src.demo.replay_dates import shift_date_columns

class TestDeploymentSmoke(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data_path = Path("data/processed/mumbai_aqi_daily_clean.parquet")
        cls.preds_path = Path("data/processed/holdout_predictions.parquet")
        cls.priority_path = Path("data/processed/mumbai_priority_rankings.parquet")
        cls.metrics_path = Path("reports/evaluation_metrics.json")

    def test_01_required_files_exist(self):
        """Ensure all runtime datasets and reports exist and are non-empty."""
        self.assertTrue(self.data_path.exists(), f"Missing {self.data_path}")
        self.assertTrue(self.preds_path.exists(), f"Missing {self.preds_path}")
        self.assertTrue(self.priority_path.exists(), f"Missing {self.priority_path}")
        self.assertTrue(self.metrics_path.exists(), f"Missing {self.metrics_path}")

        self.assertGreater(self.data_path.stat().st_size, 1000)
        self.assertGreater(self.preds_path.stat().st_size, 1000)
        self.assertGreater(self.priority_path.stat().st_size, 1000)

    def test_02_dataset_loading_and_schemas(self):
        """Verify datasets load cleanly with proper columns."""
        daily_df = pd.read_parquet(self.data_path)
        preds_df = pd.read_parquet(self.preds_path)
        priority_df = pd.read_parquet(self.priority_path)

        self.assertFalse(daily_df.empty)
        self.assertFalse(preds_df.empty)
        self.assertFalse(priority_df.empty)

        self.assertIn("canonical_station", daily_df.columns)
        self.assertIn("aqi_mean", daily_df.columns)
        self.assertIn("date", daily_df.columns)

        self.assertIn("canonical_station", preds_df.columns)
        self.assertIn("prob_unhealthy", preds_df.columns)
        self.assertIn("pred_gb", preds_df.columns)

        self.assertIn("station", priority_df.columns)
        self.assertIn("priority_score", priority_df.columns)
        self.assertIn("rank", priority_df.columns)

    def test_03_secrets_handling_graceful_fallback(self):
        """Verify get_secret safely returns default when key is missing."""
        val = get_secret("NON_EXISTENT_KEY_XYZ_123", default="fallback_val")
        self.assertEqual(val, "fallback_val")

        none_val = get_secret("ANOTHER_MISSING_KEY")
        self.assertIsNone(none_val)

    def test_04_attribution_and_branding_integrity(self):
        """Verify mandatory hackathon attribution strings."""
        self.assertEqual(EVENT_NAME, "HackAMatch 1.0")
        self.assertIn("Ratnesh", TEAM_MEMBERS)
        self.assertIn("Rishi", TEAM_MEMBERS)
        self.assertIn("Shreya", TEAM_MEMBERS)
        self.assertIn("prototype", DISCLAIMER_TEXT.lower())

    def test_05_chart_rendering(self):
        """Verify all core Plotly chart builders return valid Figure objects."""
        daily_df = pd.read_parquet(self.data_path)
        preds_df = pd.read_parquet(self.preds_path)
        priority_df = pd.read_parquet(self.priority_path)

        sample_station = priority_df["station"].iloc[0]

        fig_map = charts.plot_priority_map(priority_df, selected_station=sample_station)
        self.assertIsInstance(fig_map, go.Figure)

        default_weights = {"w_exp": 0.30, "w_pers": 0.25, "w_trend": 0.15, "w_fore": 0.20, "w_gap": 0.10}
        fig_score = charts.plot_score_breakdown(priority_df.iloc[0].to_dict(), default_weights)
        self.assertIsInstance(fig_score, go.Figure)

        st_daily = daily_df[daily_df["canonical_station"] == sample_station]
        fig_ts = charts.plot_timeseries_trajectory(st_daily, sample_station)
        self.assertIsInstance(fig_ts, go.Figure)

        st_preds = preds_df[preds_df["canonical_station"] == sample_station]
        fig_fore = charts.plot_holdout_forecast(st_preds, sample_station)
        self.assertIsInstance(fig_fore, go.Figure)

        fig_cal = charts.plot_calibration_and_pr(preds_df)
        self.assertIsInstance(fig_cal, go.Figure)

        fig_parity = charts.plot_predicted_vs_actual(preds_df)
        self.assertIsInstance(fig_parity, go.Figure)

    def test_06_entrypoint_compilation(self):
        """Verify app.py and streamlit_app.py compile without syntax errors."""
        py_compile.compile("app.py", doraise=True)
        py_compile.compile("streamlit_app.py", doraise=True)

    def test_07_priority_replay_accepts_arrow_string_dates(self):
        priority = pd.read_parquet(self.priority_path).head(2)
        priority["date"] = priority["date"].astype("string[pyarrow]")
        priority["target_date"] = priority["target_date"].astype("string[pyarrow]")
        before = pd.to_datetime(priority["date"]).copy()
        delta = pd.Timedelta(days=3)
        shift_date_columns(priority, ("date", "target_date"), delta)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(priority["date"]))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(priority["target_date"]))
        pd.testing.assert_series_equal(priority["date"], before + delta)

if __name__ == "__main__":
    unittest.main()
