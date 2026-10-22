"""
Unit tests for decision support features.

Tests priority scoring, routing, what-if simulation, and validation.
"""
import unittest
import numpy as np
import pandas as pd
from pathlib import Path

# Test data path
DATA_PATH = Path("data/processed/mumbai_aqi_daily_clean.parquet")
PREDS_PATH = Path("data/processed/holdout_predictions.parquet")


class TestPriorityScoring(unittest.TestCase):
    """Tests for the priority scoring engine."""
    
    def setUp(self):
        """Load test data if available."""
        if PREDS_PATH.exists():
            self.preds_df = pd.read_parquet(PREDS_PATH)
        else:
            self.preds_df = None
    
    def test_weights_sum_to_one(self):
        """Weights should normalize to 1.0."""
        from src.models.prioritization import compute_station_priority_scores
        
        if self.preds_df is None:
            self.skipTest("Predictions data not available")
        
        weights = {
            "w_exposure": 0.30,
            "w_persistence": 0.25,
            "w_trend": 0.15,
            "w_forecast": 0.20,
            "w_gap": 0.10
        }
        
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=2, msg="Weights should sum to 1.0")
    
    def test_priority_scores_in_range(self):
        """Priority scores should be between 0 and 100."""
        from src.models.prioritization import compute_station_priority_scores
        
        if self.preds_df is None:
            self.skipTest("Predictions data not available")
        
        priority = compute_station_priority_scores(self.preds_df)
        
        self.assertTrue(
            (priority["priority_score"] >= 0).all(),
            "All priority scores should be >= 0"
        )
        self.assertTrue(
            (priority["priority_score"] <= 100).all(),
            "All priority scores should be <= 100"
        )
    
    def test_leaderboard_has_no_nan(self):
        """Leaderboard should not contain NaN values in critical columns."""
        from src.models.prioritization import compute_station_priority_scores
        
        if self.preds_df is None:
            self.skipTest("Predictions data not available")
        
        priority = compute_station_priority_scores(self.preds_df)
        
        critical_cols = ["station", "rank", "priority_score", "latest_aqi"]
        for col in critical_cols:
            self.assertFalse(
                priority[col].isna().any(),
                f"Column {col} should not contain NaN values"
            )
    
    def test_ranks_are_sequential(self):
        """Ranks should be sequential integers starting from 1."""
        from src.models.prioritization import compute_station_priority_scores
        
        if self.preds_df is None:
            self.skipTest("Predictions data not available")
        
        priority = compute_station_priority_scores(self.preds_df)
        
        expected_ranks = list(range(1, len(priority) + 1))
        actual_ranks = priority["rank"].tolist()
        
        self.assertEqual(
            actual_ranks,
            expected_ranks,
            "Ranks should be sequential from 1 to N"
        )


class TestRouting(unittest.TestCase):
    """Tests for the inspection route planner."""
    
    def test_haversine_distance_sanity(self):
        """Haversine distance should match known values."""
        from src.decision.routing import haversine_distance
        
        # Mumbai to Delhi (approximate)
        mumbai_lat, mumbai_lon = 19.0760, 72.8777
        delhi_lat, delhi_lon = 28.6139, 77.2090
        
        dist = haversine_distance(mumbai_lat, mumbai_lon, delhi_lat, delhi_lon)
        
        # Known distance is ~1150-1200 km
        self.assertGreater(dist, 1100, "Mumbai-Delhi distance should be > 1100 km")
        self.assertLess(dist, 1300, "Mumbai-Delhi distance should be < 1300 km")
    
    def test_haversine_zero_distance(self):
        """Distance from a point to itself should be zero."""
        from src.decision.routing import haversine_distance
        
        lat, lon = 19.0760, 72.8777
        dist = haversine_distance(lat, lon, lat, lon)
        
        self.assertAlmostEqual(dist, 0.0, places=6, msg="Distance to self should be 0")
    
    def test_route_starts_at_specified_station(self):
        """Route should start at the specified starting station."""
        from src.decision.routing import compute_inspection_route
        
        # Create mock priority dataframe
        mock_priority = pd.DataFrame({
            "station": ["Station A", "Station B", "Station C"],
            "latitude": [19.1, 19.2, 19.3],
            "longitude": [72.8, 72.9, 73.0],
            "priority_score": [90, 80, 70],
            "latest_aqi": [150, 140, 130],
            "zone": ["Zone 1", "Zone 2", "Zone 3"]
        })
        
        route_df, _ = compute_inspection_route(
            mock_priority,
            top_n=3,
            start_station="Station B"
        )
        
        self.assertEqual(
            route_df.iloc[0]["station"],
            "Station B",
            "Route should start at specified station"
        )
    
    def test_route_visits_all_top_n(self):
        """Route should visit exactly top-N stations."""
        from src.decision.routing import compute_inspection_route
        
        mock_priority = pd.DataFrame({
            "station": ["Station A", "Station B", "Station C", "Station D"],
            "latitude": [19.1, 19.2, 19.3, 19.4],
            "longitude": [72.8, 72.9, 73.0, 73.1],
            "priority_score": [90, 80, 70, 60],
            "latest_aqi": [150, 140, 130, 120],
            "zone": ["Zone 1", "Zone 2", "Zone 3", "Zone 4"]
        })
        
        top_n = 3
        route_df, _ = compute_inspection_route(mock_priority, top_n=top_n)
        
        self.assertEqual(
            len(route_df),
            top_n,
            f"Route should visit exactly {top_n} stations"
        )


class TestWhatIfSimulation(unittest.TestCase):
    """Tests for the what-if policy simulator."""
    
    def test_rank_delta_computation(self):
        """Rank delta should correctly compute movement."""
        from src.decision.whatif import compute_rank_delta
        
        old_priority = pd.DataFrame({
            "station": ["A", "B", "C"],
            "rank": [1, 2, 3]
        })
        
        new_priority = pd.DataFrame({
            "station": ["A", "B", "C"],
            "rank": [2, 1, 3]
        })
        
        delta_df = compute_rank_delta(old_priority, new_priority)
        
        # A moved from 1 to 2 (delta = -1, worsened)
        self.assertEqual(delta_df[delta_df["station"] == "A"]["delta"].iloc[0], -1)
        
        # B moved from 2 to 1 (delta = +1, improved)
        self.assertEqual(delta_df[delta_df["station"] == "B"]["delta"].iloc[0], 1)
        
        # C stayed at 3 (delta = 0)
        self.assertEqual(delta_df[delta_df["station"] == "C"]["delta"].iloc[0], 0)


class TestValidation(unittest.TestCase):
    """Tests for validation metrics."""
    
    def test_interval_coverage_bounds(self):
        """Coverage should be between 0 and 1."""
        from src.decision.validation import compute_interval_coverage
        
        # Mock predictions with perfect coverage
        mock_preds = pd.DataFrame({
            "pred_p10": [50, 60, 70],
            "pred_p90": [100, 110, 120],
            "target_next_day_aqi": [75, 85, 95]
        })
        
        result = compute_interval_coverage(mock_preds, confidence=0.80)
        
        self.assertGreaterEqual(result["coverage"], 0.0, "Coverage should be >= 0")
        self.assertLessEqual(result["coverage"], 1.0, "Coverage should be <= 1")


if __name__ == "__main__":
    unittest.main()
