import unittest

import pandas as pd

from src.decision.reliability import station_reliability


class TestStationReliability(unittest.TestCase):
    def test_missing_calendar_days_count_as_missing_hours(self):
        daily = pd.DataFrame({
            "canonical_station": ["A", "A", "A"],
            "date": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "valid_hours": [24, 12, 24],
        })

        result = station_reliability(daily, pd.Timestamp("2023-01-04"), days=4).iloc[0]

        self.assertEqual(result["observed_hours"], 60)
        self.assertEqual(result["expected_hours"], 96)
        self.assertEqual(result["coverage_pct"], 62.5)
        self.assertEqual(result["missing_hours_pct"], 37.5)
        self.assertEqual(result["valid_days"], 2)
        self.assertEqual(result["confidence"], "Low")

    def test_confidence_thresholds(self):
        dates = pd.date_range("2023-01-01", periods=30)
        daily = pd.DataFrame({
            "canonical_station": ["A"] * 30 + ["B"] * 30,
            "date": list(dates) * 2,
            "valid_hours": [24] * 30 + [20] * 30,
        })

        result = station_reliability(daily, dates[-1]).set_index("station")

        self.assertEqual(result.loc["A", "confidence"], "High")
        self.assertEqual(result.loc["B", "confidence"], "Medium")


if __name__ == "__main__":
    unittest.main()
