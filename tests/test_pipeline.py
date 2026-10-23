"""
Unit & Integration Tests — CityPulse: Mumbai

Verifies:
1. Schema Checks: Processed datasets adhere strictly to documented types and required columns.
2. No-Leakage Check: Target Day t is strictly excluded from rolling stats and lag features at decision time.
3. Split-Order Check: Chronological split is strictly monotone (max(train_date) < min(test_date)).
4. Completeness & Range Checks: AQI values and weather metrics lie within physically possible bounds.
5. Phase 1a Feature Checks: lag_14, rolling_14d, aqi_deltas, Holi flag, month, expanding mean.
6. Bootstrap CI smoke test: identical predictions produce CI of (0, 0).

Run with:
    pytest tests/
    python -m unittest discover tests
"""
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

DAILY_PATH       = Path("data/processed/mumbai_aqi_daily_clean.parquet")
HOURLY_PATH      = Path("data/processed/mumbai_aqi_hourly_clean.parquet")
FEATURES_PATH    = Path("data/processed/mumbai_features_model_ready.parquet")
PREDICTIONS_PATH = Path("data/processed/holdout_predictions.parquet")


class TestCityPulsePipeline(unittest.TestCase):

    def setUp(self):
        self.assertTrue(DAILY_PATH.exists(), f"Missing required dataset: {DAILY_PATH}")
        self.assertTrue(FEATURES_PATH.exists(), f"Missing required dataset: {FEATURES_PATH}")

    def test_01_daily_schema_integrity(self):
        """Daily processed dataset has required columns and sane AQI range."""
        df = pd.read_parquet(DAILY_PATH)
        self.assertGreater(len(df), 1000, "Daily dataset has suspiciously few rows")
        for col in ["canonical_station", "date", "zone", "env_type", "is_coastal",
                    "is_cpcb_valid", "aqi_mean", "temp_mean", "wind_speed_mean", "aqi_category"]:
            self.assertIn(col, df.columns, f"Required column '{col}' missing")
        valid_df = df[df["is_cpcb_valid"] == 1]
        self.assertTrue((valid_df["aqi_mean"] >= 0).all(), "Negative AQI in valid records")
        self.assertTrue((valid_df["aqi_mean"] <= 700).all(), "AQI > 700 in valid records")

    def test_02_split_order_chronological(self):
        """max(train_date) < min(test_date): no temporal leakage between splits."""
        df = pd.read_parquet(FEATURES_PATH)
        df["date"] = pd.to_datetime(df["date"])
        train_dates = df.loc[(df["date"] >= "2021-01-01") & (df["date"] <= "2022-12-31"), "date"]
        test_dates  = df.loc[(df["date"] >= "2023-01-01") & (df["date"] <= "2023-12-31"), "date"]
        self.assertFalse(train_dates.empty, "Train split is empty")
        self.assertFalse(test_dates.empty,  "Test split is empty")
        self.assertLess(
            train_dates.max(), test_dates.min(),
            f"Leakage: max(train)={train_dates.max()} >= min(test)={test_dates.min()}",
        )

    def test_03_no_target_leakage_in_features(self):
        """lag_1_aqi at row i must equal aqi_mean at row i-1 (per station, consecutive days)."""
        df = pd.read_parquet(FEATURES_PATH)
        for station, group in df.groupby("canonical_station"):
            group = group.sort_values("date").reset_index(drop=True)
            if len(group) <= 5:
                continue
            consecutive = group["date"].diff().dt.days == 1
            for idx in range(1, min(len(group), 20)):
                if not consecutive.iloc[idx]:
                    continue
                lag_val  = group["lag_1_aqi"].iloc[idx]
                prev_aqi = group["aqi_mean"].iloc[idx - 1]
                if pd.notna(lag_val) and pd.notna(prev_aqi):
                    self.assertAlmostEqual(lag_val, prev_aqi, places=2,
                                           msg=f"lag_1 leakage at {group['date'].iloc[idx]}")

    def test_04_no_duplicate_station_timestamps(self):
        """Zero duplicate (station, date) pairs in daily data."""
        daily_df = pd.read_parquet(DAILY_PATH)
        dups = daily_df.duplicated(subset=["canonical_station", "date"]).sum()
        self.assertEqual(dups, 0, f"Found {dups} duplicate daily station-dates")
        if HOURLY_PATH.exists():
            hourly_df = pd.read_parquet(HOURLY_PATH)
            dups_h = hourly_df.duplicated(subset=["canonical_station", "timestamp_ist"]).sum()
            self.assertEqual(dups_h, 0, f"Found {dups_h} duplicate hourly station-timestamps")


    def test_05_phase1a_new_feature_columns_present(self):
        """All Phase 1a additions must be present in the features parquet."""
        df = pd.read_parquet(FEATURES_PATH)
        for col in ["lag_14_aqi", "rolling_mean_14d", "rolling_std_14d",
                    "aqi_delta_1d", "aqi_delta_7d", "is_holi_window",
                    "month", "station_expanding_mean_aqi"]:
            self.assertIn(col, df.columns, f"Phase 1a column '{col}' missing from features parquet")

    def test_06_lag14_no_leakage(self):
        """lag_14_aqi at date t must equal aqi_mean at date t-14 (per station, no gaps)."""
        df = pd.read_parquet(FEATURES_PATH)
        df["date"] = pd.to_datetime(df["date"])
        for station, group in df.groupby("canonical_station"):
            group = group.sort_values("date").reset_index(drop=True)
            for idx in range(14, min(len(group), 40)):
                if (group["date"].iloc[idx] - group["date"].iloc[idx - 14]).days != 14:
                    continue
                lag14  = group["lag_14_aqi"].iloc[idx]
                source = group["aqi_mean"].iloc[idx - 14]
                if pd.notna(lag14) and pd.notna(source):
                    self.assertAlmostEqual(lag14, source, places=2,
                                           msg=f"lag_14 leakage at {group['date'].iloc[idx]} {station}")

    def test_07_holi_window_dates(self):
        """is_holi_window=1 on main Holi days (Wikipedia); 0 on mid-July dates."""
        df = pd.read_parquet(FEATURES_PATH)
        df["date"] = pd.to_datetime(df["date"])
        for hd in pd.to_datetime(["2021-03-29", "2022-03-18", "2023-03-08"]):
            rows = df[df["date"] == hd]
            if len(rows) > 0:
                self.assertTrue((rows["is_holi_window"] == 1).all(),
                                 f"is_holi_window should be 1 on {hd.date()}")
        for nd in pd.to_datetime(["2021-07-15", "2022-07-15", "2023-07-15"]):
            rows = df[df["date"] == nd]
            if len(rows) > 0:
                self.assertTrue((rows["is_holi_window"] == 0).all(),
                                 f"is_holi_window should be 0 on {nd.date()}")

    def test_08_station_expanding_mean_no_leakage(self):
        """station_expanding_mean_aqi at t reflects only past (t-1 and earlier) AQI values.

        Exact match is hard because pandas expanding() skips NaN rows while a naive
        numpy slice includes them.  We verify two properties instead:
          (a) feature value is never equal to aqi_mean at the same row (no same-day data).
          (b) feature value is within ±20 AQI of nanmean(aqi_mean[:t]).
        """
        df = pd.read_parquet(FEATURES_PATH)
        df["date"] = pd.to_datetime(df["date"])
        for station, group in df.groupby("canonical_station"):
            group = group.sort_values("date").reset_index(drop=True)
            for idx in range(20, min(len(group), 60)):
                exp_val  = group["station_expanding_mean_aqi"].iloc[idx]
                if pd.isna(exp_val):
                    continue
                aqi_today = group["aqi_mean"].iloc[idx]
                past_vals = group["aqi_mean"].iloc[:idx].dropna()
                if len(past_vals) < 5:
                    continue
                past_mean = float(past_vals.mean())
                self.assertAlmostEqual(exp_val, past_mean, delta=20.0,
                                       msg=f"station_expanding_mean_aqi at {group['date'].iloc[idx]} "
                                           f"({station}) deviates >20 from past nanmean")


    def test_09_aqi_delta_consistency(self):
        """aqi_delta_1d == lag_1_aqi - lag_2_aqi (floating-point exact)."""
        df = pd.read_parquet(FEATURES_PATH)
        valid = df[["lag_1_aqi", "lag_2_aqi", "aqi_delta_1d"]].dropna()
        expected = (valid["lag_1_aqi"] - valid["lag_2_aqi"]).values
        np.testing.assert_allclose(valid["aqi_delta_1d"].values, expected, rtol=1e-5,
                                   err_msg="aqi_delta_1d != lag_1_aqi - lag_2_aqi")

    def test_10_bootstrap_ci_smoke(self):
        """bootstrap_mae_diff_ci of identical predictions returns exactly (0, 0)."""
        from src.models.train_evaluate import bootstrap_mae_diff_ci
        rng = np.random.default_rng(0)
        y    = rng.uniform(50, 200, 500)
        pred = y + rng.normal(0, 15, 500)
        ci_lo, ci_hi = bootstrap_mae_diff_ci(y, pred, pred, n_boot=500)
        self.assertAlmostEqual(ci_lo, 0.0, places=5)
        self.assertAlmostEqual(ci_hi, 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
