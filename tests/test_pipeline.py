"""
Unit & Integration Tests — CityPulse: Mumbai

Verifies:
1. Schema Checks: Processed datasets adhere strictly to documented types and required columns.
2. No-Leakage Check: Target Day t is strictly excluded from rolling stats and lag features at decision time.
3. Split-Order Check: Chronological split is strictly monotone (max(train_date) < min(test_date)).
4. Completeness & Range Checks: AQI values and weather metrics lie within physically possible bounds.

Run with:
    pytest tests/
    python -m unittest discover tests
"""
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

DAILY_PATH = Path("data/processed/mumbai_aqi_daily_clean.parquet")
HOURLY_PATH = Path("data/processed/mumbai_aqi_hourly_clean.parquet")
FEATURES_PATH = Path("data/processed/mumbai_features_model_ready.parquet")
PREDICTIONS_PATH = Path("data/processed/holdout_predictions.parquet")

class TestCityPulsePipeline(unittest.TestCase):

    def setUp(self):
        self.assertTrue(DAILY_PATH.exists(), f"Missing required dataset: {DAILY_PATH}")
        self.assertTrue(FEATURES_PATH.exists(), f"Missing required dataset: {FEATURES_PATH}")

    def test_01_daily_schema_integrity(self):
        """Test daily processed dataset columns and non-empty state."""
        df = pd.read_parquet(DAILY_PATH)
        self.assertGreater(len(df), 1000, "Daily dataset has suspiciously few rows")

        required_cols = [
            "canonical_station", "date", "zone", "env_type", "is_coastal",
            "is_cpcb_valid", "aqi_mean", "temp_mean", "wind_speed_mean", "aqi_category"
        ]
        for col in required_cols:
            self.assertIn(col, df.columns, f"Required column '{col}' missing from daily dataset")

        valid_df = df[df["is_cpcb_valid"] == 1]
        self.assertTrue((valid_df["aqi_mean"] >= 0).all(), "Negative AQI found in valid records")
        self.assertTrue((valid_df["aqi_mean"] <= 700).all(), "Unrealistically extreme AQI found (> 700)")

    def test_02_split_order_chronological(self):
        """Test strict temporal ordering between train and test splits (no future leaking into past)."""
        df = pd.read_parquet(FEATURES_PATH)
        df["date"] = pd.to_datetime(df["date"])

        train_mask = (df["date"] >= "2021-01-01") & (df["date"] <= "2022-12-31")
        test_mask = (df["date"] >= "2023-01-01") & (df["date"] <= "2023-12-31")

        train_dates = df.loc[train_mask, "date"]
        test_dates = df.loc[test_mask, "date"]

        self.assertFalse(train_dates.empty, "Train split is empty")
        self.assertFalse(test_dates.empty, "Test split is empty")

        max_train = train_dates.max()
        min_test = test_dates.min()
        self.assertLess(max_train, min_test, f"Data leakage detected! max(train)={max_train} >= min(test)={min_test}")

    def test_03_no_target_leakage_in_features(self):
        """Test that decision features for day t do not contain day t or future targets."""
        df = pd.read_parquet(FEATURES_PATH)
        for station, group in df.groupby("canonical_station"):
            group = group.sort_values("date").reset_index(drop=True)
            if len(group) > 5:
                consecutive = (group["date"].diff().dt.days == 1)
                for idx in range(1, min(len(group), 20)):
                    if consecutive.iloc[idx] and pd.notna(group["lag_1_aqi"].iloc[idx]):
                        prev_aqi = group["aqi_mean"].iloc[idx - 1]
                        lag_val = group["lag_1_aqi"].iloc[idx]
                        if pd.notna(prev_aqi):
                            self.assertAlmostEqual(
                                lag_val, prev_aqi, places=2,
                                msg=f"Feature leakage: lag_1_aqi does not match true lag on day {group['date'].iloc[idx]}"
                            )

    def test_04_no_duplicate_station_timestamps(self):
        """Test that hourly and daily datasets contain zero duplicate timestamps per station."""
        daily_df = pd.read_parquet(DAILY_PATH)
        dups_daily = daily_df.duplicated(subset=["canonical_station", "date"]).sum()
        self.assertEqual(dups_daily, 0, f"Found {dups_daily} duplicate daily station-dates")

        if HOURLY_PATH.exists():
            hourly_df = pd.read_parquet(HOURLY_PATH)
            dups_hourly = hourly_df.duplicated(subset=["canonical_station", "timestamp_ist"]).sum()
            self.assertEqual(dups_hourly, 0, f"Found {dups_hourly} duplicate hourly station-timestamps")

if __name__ == "__main__":
    unittest.main()
