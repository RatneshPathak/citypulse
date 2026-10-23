import subprocess
import unittest
from unittest.mock import patch

import Evaluate
import numpy as np
import pandas as pd


class TestEvaluateScript(unittest.TestCase):
    def test_failed_test_process_is_reported_as_failed(self):
        result = subprocess.CompletedProcess(
            args=["python", "-m", "unittest", "discover", "tests"],
            returncode=1,
            stdout="",
            stderr="Ran 3 tests in 0.01s\n\nFAILED\n",
        )
        with patch.object(Evaluate.subprocess, "run", return_value=result):
            summary = Evaluate.stage_2_test_suite()
        self.assertEqual(summary["status"], "FAIL")
        self.assertEqual(summary["passed"], 0)

    def test_uses_final_unittest_summary(self):
        result = subprocess.CompletedProcess(
            args=["python", "-m", "unittest", "discover", "tests"],
            returncode=0,
            stdout="Fixture output: Ran 3 tests in 0.01s\nFAILED\n",
            stderr="Ran 40 tests in 2.00s\n\nOK\n",
        )
        with patch.object(Evaluate.subprocess, "run", return_value=result):
            summary = Evaluate.stage_2_test_suite()
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["total"], 40)
        self.assertEqual(summary["passed"], 40)

    def test_holdout_report_uses_date_bootstrap_on_synthetic_data(self):
        dates = pd.date_range("2021-01-01", "2023-02-01", freq="D")
        values = 100 + 10 * np.sin(np.arange(len(dates)) / 10)
        frame = pd.DataFrame({
            "date": dates,
            "canonical_station": "Synthetic station",
            "target_next_day_aqi": values,
            "lag_1_aqi": np.r_[values[0], values[:-1]],
            "lag_7_aqi": np.r_[np.repeat(values[0], 7), values[:-7]],
        })
        with patch.object(Evaluate, "date_bootstrap_ci", wraps=Evaluate.date_bootstrap_ci) as bootstrap:
            result = Evaluate.stage_5_holdout_evaluation(
                frame, best_model_name="Persistence", features_to_use=["lag_1_aqi"], n_boot=20,
            )
        self.assertEqual(bootstrap.call_count, 3)
        self.assertEqual(result["best_model_name"], "Persistence")


if __name__ == "__main__":
    unittest.main()
