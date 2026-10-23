"""
CityPulse: Mumbai — What-If Policy Simulator

Interactive weight sensitivity analysis and rank stability simulation.
Shows how priority rankings change under different policy weights.
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple
import streamlit as st

@st.cache_data(ttl=3600)
def compute_rank_stability(
    preds_df: pd.DataFrame,
    baseline_weights: Dict[str, float],
    n_simulations: int = 500,
    perturbation_pct: float = 0.30,
    target_n: int = 5
) -> pd.DataFrame:
    """
    Runs Monte Carlo simulation to assess rank stability under weight perturbations.
    
    Parameters
    ----------
    preds_df : pd.DataFrame
        Predictions dataframe with station features
    baseline_weights : dict
        Baseline policy weights
    n_simulations : int
        Number of random weight perturbations to simulate
    perturbation_pct : float
        Max perturbation as fraction (0.30 = ±30%)
    target_n : int
        Top-N threshold for probability calculation
    
    Returns
    -------
    pd.DataFrame
        Columns: station, prob_top_n, rank_min, rank_max, rank_mean, rank_std
    """
    from src.models.prioritization import compute_station_priority_scores
    
    np.random.seed(42)
    
    baseline_priority = compute_station_priority_scores(
        preds_df,
        w_exposure=baseline_weights["w_exp"],
        w_persistence=baseline_weights["w_pers"],
        w_trend=baseline_weights["w_trend"],
        w_forecast=baseline_weights["w_fore"],
        w_gap=baseline_weights["w_gap"],
    )
    
    stations = baseline_priority["station"].tolist()
    rank_history = {station: [] for station in stations}
    
    for _ in range(n_simulations):
        perturbed = {}
        for key, val in baseline_weights.items():
            noise = np.random.uniform(-perturbation_pct, perturbation_pct)
            perturbed[key] = max(0.01, val * (1 + noise))
        
        total = sum(perturbed.values())
        perturbed = {k: v/total for k, v in perturbed.items()}
        
        sim_priority = compute_station_priority_scores(
            preds_df,
            w_exposure=perturbed["w_exp"],
            w_persistence=perturbed["w_pers"],
            w_trend=perturbed["w_trend"],
            w_forecast=perturbed["w_fore"],
            w_gap=perturbed["w_gap"],
        )
        
        for _, row in sim_priority.iterrows():
            rank_history[row["station"]].append(row["rank"])
    
    results = []
    for station in stations:
        ranks = rank_history[station]
        prob_top_n = sum(1 for r in ranks if r <= target_n) / len(ranks)
        results.append({
            "station": station,
            "prob_top_n": prob_top_n,
            "rank_min": int(np.min(ranks)),
            "rank_max": int(np.max(ranks)),
            "rank_mean": float(np.mean(ranks)),
            "rank_std": float(np.std(ranks)),
            "rank_range": int(np.max(ranks) - np.min(ranks)),
        })
    
    return pd.DataFrame(results).sort_values("prob_top_n", ascending=False)

def compute_rank_delta(
    old_priority: pd.DataFrame,
    new_priority: pd.DataFrame
) -> pd.DataFrame:
    """
    Computes rank movement between two priority rankings.
    
    Returns DataFrame with columns: station, old_rank, new_rank, delta, movement
    """
    old_ranks = old_priority[["station", "rank"]].rename(columns={"rank": "old_rank"})
    new_ranks = new_priority[["station", "rank"]].rename(columns={"rank": "new_rank"})
    
    merged = old_ranks.merge(new_ranks, on="station")
    merged["delta"] = merged["old_rank"] - merged["new_rank"]
    
    def get_movement(delta):
        if delta > 0:
            return f"↑ +{int(delta)}"
        elif delta < 0:
            return f"↓ {int(delta)}"
        else:
            return "—"
    
    merged["movement"] = merged["delta"].apply(get_movement)
    
    return merged.sort_values("new_rank")
