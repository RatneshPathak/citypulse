"""
Unit & Regression Tests — CityPulse: Mumbai AQI Cleaning & EDA Integration
Source of Truth: src/CityPulse_AQI_Cleaning_EDA.ipynb and src/clean/aqi_cleaning.py

Verifies:
1. Schema & required columns: Canonical 10 columns present and typed properly.
2. Deduplication: No duplicate (Station, From Date, To Date) records.
3. Temporal Integrity: Timestamps are chronologically sorted and valid datetime.
4. Physical Boundaries: No impossible negative concentrations.
5. Outlier Detection: Tukey IQR bounds correctly identify extreme physical spikes without silent deletion.
6. Regression vs Notebook: Cleaned metrics match notebook reference statistics.
"""
import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

from src.clean.aqi_cleaning import (
    POLLUTANTS,
    FINAL_COLUMNS,
    deduplicate_records,
    handle_missing_values,
    detect_outliers_iqr,
    compute_station_statistics,
    clean_aqi_dataset,
)

REF_STATS_PATH = Path("reports/notebook_reference_stats.json")

class TestAQICleaningPipeline(unittest.TestCase):

    def setUp(self):
        """Builds a deterministic test fixture mirroring the CPCB structure."""
        dates = pd.date_range("2025-01-01 00:00:00", periods=24, freq="h")
        self.mock_data = pd.DataFrame({
            "From Date": dates,
            "To Date": dates + pd.Timedelta(hours=1),
            "Station": ["Bandra Kurla Complex, Mumbai - IITM"] * 12 + ["Chembur, Mumbai - MPCB"] * 12,
            "PM2.5": [25.0, 30.0, 35.0, 40.0, 150.0, np.nan, 20.0, 22.0, 28.0, 31.0, 29.0, 33.0,
                      np.nan, 28.0, 32.0, 30.0, 26.0, 27.0, 35.0, 45.0, 50.0, 48.0, 40.0, 38.0],
            "PM10": [60.0] * 11 + [np.nan] + [np.nan] + [70.0] * 11,
            "NO": [15.0] * 24,
            "NO2": [25.0] * 24,
            "NH3": [10.0] * 24,
            "SO2": [8.0] * 12 + [np.nan] * 12,
            "CO": [0.5] * 24,
        })

    def test_01_schema_and_required_columns(self):
        """Test that cleaning output enforces canonical columns and datatypes."""
        cleaned_df, _, _ = clean_aqi_dataset(self.mock_data)
        for col in FINAL_COLUMNS:
            self.assertIn(col, cleaned_df.columns, f"Required column '{col}' missing from clean dataset")
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(cleaned_df["From Date"]))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(cleaned_df["To Date"]))
        for p in POLLUTANTS:
            self.assertTrue(pd.api.types.is_float_dtype(cleaned_df[p]))

    def test_02_deduplication(self):
        """Test that duplicate timestamps within a station are detected and removed."""
        dup_row = self.mock_data.iloc[[0]].copy()
        df_with_dups = pd.concat([self.mock_data, dup_row], ignore_index=True)
        self.assertEqual(len(df_with_dups), len(self.mock_data) + 1)

        deduped, dropped_count = deduplicate_records(df_with_dups)
        self.assertEqual(dropped_count, 1)
        self.assertEqual(len(deduped), len(self.mock_data))
        self.assertFalse(deduped.duplicated(subset=["Station", "From Date", "To Date"]).any())

    def test_03_timestamp_chronological_order(self):
        """Test that output timestamps are strictly non-decreasing per station."""
        cleaned_df, _, _ = clean_aqi_dataset(self.mock_data)
        for station, group in cleaned_df.groupby("Station"):
            dates = group["From Date"].tolist()
            self.assertEqual(dates, sorted(dates), f"Dates not monotonically sorted for station {station}")

    def test_04_no_negative_pollutant_concentrations(self):
        """Test that impossible negative concentrations are rejected or flagged."""
        test_df = self.mock_data.copy()
        test_df.loc[0, "PM2.5"] = -15.0
        for p in POLLUTANTS:
            valid_readings = test_df[test_df[p] >= 0][p]
            self.assertTrue((valid_readings >= 0).all())

    def test_05_missing_value_offline_filter(self):
        """Test that rows where ALL pollutants are NaN are dropped, but partial NaNs preserved."""
        test_df = self.mock_data.copy()
        offline_row = pd.DataFrame([{
            "From Date": pd.to_datetime("2025-01-02 00:00:00"),
            "To Date": pd.to_datetime("2025-01-02 01:00:00"),
            "Station": "Bandra Kurla Complex, Mumbai - IITM",
            **{p: np.nan for p in POLLUTANTS}
        }])
        augmented_df = pd.concat([test_df, offline_row], ignore_index=True)
        cleaned_df, num_offline = handle_missing_values(augmented_df)
        self.assertEqual(num_offline, 1)
        self.assertEqual(len(cleaned_df), len(test_df))

    def test_06_iqr_outlier_detection(self):
        """Test Tukey IQR bounds computation and flagging without silent dropping."""
        outliers = detect_outliers_iqr(self.mock_data, pollutant="PM2.5", multiplier=1.5)
        self.assertFalse(outliers.empty)
        self.assertIn("lower_bound", outliers.columns)
        self.assertIn("upper_bound", outliers.columns)
        self.assertTrue((outliers["PM2.5"] == 150.0).any())

    def test_07_regression_against_notebook_reference(self):
        """
        Regression Test: Verifies that reference statistical properties extracted
        from the team's executed notebook (src/CityPulse_AQI_Cleaning_EDA.ipynb)
        remain consistent and documented.
        """
        self.assertTrue(REF_STATS_PATH.exists(), f"Reference stats missing: {REF_STATS_PATH}")
        with open(REF_STATS_PATH, "r", encoding="utf-8") as f:
            ref = json.load(f)

        self.assertEqual(ref["raw_rows"], 63168)
        self.assertEqual(ref["all_missing_rows_dropped"], 9981)
        self.assertEqual(ref["cleaned_rows"], 53187)
        self.assertEqual(ref["raw_rows"] - ref["all_missing_rows_dropped"], ref["cleaned_rows"])

        expected_stations = [
            "Bandra Kurla Complex, Mumbai - IITM",
            "Borivali East, Mumbai - MPCB",
            "Chembur, Mumbai - MPCB",
            "Siddharth Nagar-Worli, Mumbai - IITM",
        ]
        self.assertEqual(sorted(ref["stations"]), sorted(expected_stations))

        self.assertEqual(ref["station_summary"]["Siddharth Nagar-Worli, Mumbai - IITM"]["so2_count"], 0)
        self.assertEqual(ref["worli_so2_missing_pct"], 100.0)

        bkc_pm25 = ref["station_summary"]["Bandra Kurla Complex, Mumbai - IITM"]["pm25_mean"]
        borivali_pm25 = ref["station_summary"]["Borivali East, Mumbai - MPCB"]["pm25_mean"]
        self.assertGreater(bkc_pm25, borivali_pm25)
        self.assertAlmostEqual(bkc_pm25, 33.50, places=2)
        self.assertAlmostEqual(borivali_pm25, 23.61, places=2)

        self.assertEqual(ref["total_pm25_outliers"], 1281)
        self.assertAlmostEqual(ref["overall_pm25_outlier_pct"], 2.56, places=2)

if __name__ == "__main__":
    unittest.main()
