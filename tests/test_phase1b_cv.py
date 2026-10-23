import unittest

import numpy as np
import pandas as pd

from src.features.build_features import construct_features
from src.models.phase1b_cv import inner_date_splits


class TestPhase1bCV(unittest.TestCase):
    def test_inner_splits_are_strictly_chronological(self):
        dates = pd.date_range("2021-01-01", "2022-08-31", freq="D")
        frame = pd.DataFrame({"date": dates})
        for train_idx, test_idx in inner_date_splits(frame):
            self.assertLess(frame.iloc[train_idx]["date"].max(), frame.iloc[test_idx]["date"].min())

    def test_station_expanding_mean_excludes_current_and_future_aqi(self):
        dates = pd.date_range("2021-01-01", periods=160, freq="D")
        source = pd.DataFrame({
            "canonical_station": "Test station", "date": dates,
            "is_cpcb_valid": 1, "aqi_mean": np.arange(160, dtype=float) + 30,
        })
        original = construct_features(source)
        changed = source.copy()
        changed.loc[changed.index >= 100, "aqi_mean"] = 9999.0
        revised = construct_features(changed)
        date = dates[100]
        previous_values = source.loc[source["date"] < date, "aqi_mean"]
        prior_mean = float(previous_values.mean())
        before = original.loc[original["date"] == date, "station_expanding_mean_aqi"].iloc[0]
        after = revised.loc[revised["date"] == date, "station_expanding_mean_aqi"].iloc[0]
        self.assertAlmostEqual(before, prior_mean)
        self.assertAlmostEqual(after, prior_mean)


if __name__ == "__main__":
    unittest.main()
