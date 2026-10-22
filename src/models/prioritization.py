"""
Risk Prioritisation & Decision-Support Engine (ACT) — CityPulse: Mumbai

Computes an explainable, multi-criteria Priority Score for municipal
health and environmental officers (BMC / MPCB):

Priority Score Components:
1. Exposure Severity (0-100): Recent 7-day mean AQI relative to regulatory limits.
2. Persistence Shock (0-100): Number of days in the past week crossing Moderate/Poor (AQI > 150).
3. Acceleration / Trend (0-100): Rate of worsening (7-day trend slope).
4. Predictive Risk (0-100): Calibrated probability of exceeding Unhealthy threshold (AQI > 200).
5. Vulnerability & Monitoring Gap (0-100): Siting near high-density transit corridors or monitoring gaps.

Operational Features:
- Capacity constraint simulation: "Given resource budget to inspect N zones this week, which N to select?"
- Weight sensitivity analysis: Shows how rankings shift under Exposure-heavy vs Forecast-heavy policies.
- Action generation: Translates empirical evidence into proportional, defensible municipal interventions
  without unsubstantiated source-attribution claims.

Usage:
    python -m src.models.prioritization
"""
import logging
from pathlib import Path
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PREDICTIONS_PATH = Path("data/processed/holdout_predictions.parquet")
PROCESSED_DIR = Path("data/processed")


def compute_station_priority_scores(
    df: pd.DataFrame,
    as_of_date: str | None = None,
    w_exposure: float = 0.30,
    w_persistence: float = 0.25,
    w_trend: float = 0.15,
    w_forecast: float = 0.20,
    w_gap: float = 0.10
) -> pd.DataFrame:
    """
    Computes normalized multi-criteria priority scores for all active stations
    as of a decision date (default: most recent date in holdout dataset).
    """
    if as_of_date is None:
        target_date = df["date"].max()
    else:
        target_date = pd.to_datetime(as_of_date)

    recent_window = df[(df["date"] < target_date) & (df["date"] >= target_date - pd.Timedelta(days=7))].copy()
    latest_day = df[df["date"] == target_date].copy()

    if latest_day.empty:
        target_date = df["date"].max()
        recent_window = df[(df["date"] < target_date) & (df["date"] >= target_date - pd.Timedelta(days=7))].copy()
        latest_day = df[df["date"] == target_date].copy()

    records = []
    for station, grp in recent_window.groupby("canonical_station"):
        latest_row = latest_day[latest_day["canonical_station"] == station]
        if latest_row.empty:
            continue
        row = latest_row.iloc[0]

        recent_mean_aqi = grp["target_next_day_aqi"].mean()
        score_exposure = np.clip((recent_mean_aqi - 50.0) / 250.0 * 100.0, 0, 100)

        days_above_150 = (grp["target_next_day_aqi"] > 150).sum()
        score_persistence = np.clip((days_above_150 / 7.0) * 100.0, 0, 100)

        trend = row.get("trend_7d", 0.0)
        score_trend = np.clip((trend + 30.0) / 60.0 * 100.0, 0, 100)

        prob_unhealthy = row.get("prob_unhealthy", 0.0)
        score_forecast = np.clip(prob_unhealthy * 100.0, 0, 100)

        env = row.get("env_type", "")
        vuln_base = 50.0
        if any(k in env.lower() for k in ["highway", "industrial", "traffic", "dumping", "aviation"]):
            vuln_base = 80.0
        elif "coastal" in env.lower() or "park" in env.lower():
            vuln_base = 30.0
        score_gap = vuln_base

        total_weight = w_exposure + w_persistence + w_trend + w_forecast + w_gap
        priority_score = (
            w_exposure * score_exposure +
            w_persistence * score_persistence +
            w_trend * score_trend +
            w_forecast * score_forecast +
            w_gap * score_gap
        ) / total_weight

        if priority_score >= 70:
            tier = "Tier 1: High Priority (Immediate Municipal Action)"
        elif priority_score >= 45:
            tier = "Tier 2: Moderate Priority (Enhanced Monitoring)"
        else:
            tier = "Tier 3: Low Priority (Routine Surveillance)"

        action_plan = generate_action_recommendation(
            station=station,
            zone=row.get("zone", "MMR"),
            env=env,
            recent_mean=recent_mean_aqi,
            days_unhealthy=days_above_150,
            prob_risk=prob_unhealthy,
            pred_interval=(row.get("pred_p10", 0), row.get("pred_p90", 0)),
            is_coastal=row.get("is_coastal", 0)
        )

        records.append({
            "station": station,
            "zone": row.get("zone", "MMR"),
            "env_type": env,
            "latitude": row.get("latitude", np.nan),
            "longitude": row.get("longitude", np.nan),
            "date": (target_date - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "target_date": target_date.strftime("%Y-%m-%d"),
            "latest_aqi": round(row["lag_1_aqi"], 1),
            "recent_7d_mean_aqi": round(recent_mean_aqi, 1),
            "days_above_150_last_week": int(days_above_150),
            "forecast_prob_unhealthy": round(prob_unhealthy, 2),
            "forecast_aqi_p10": round(row.get("pred_p10", 0), 1),
            "forecast_aqi_point": round(row.get("pred_gb", row["target_next_day_aqi"]), 1),
            "forecast_aqi_p90": round(row.get("pred_p90", 0), 1),
            "score_exposure": round(score_exposure, 1),
            "score_persistence": round(score_persistence, 1),
            "score_trend": round(score_trend, 1),
            "score_forecast": round(score_forecast, 1),
            "score_vulnerability": round(score_gap, 1),
            "priority_score": round(priority_score, 1),
            "risk_tier": tier,
            "recommended_action": action_plan["action"],
            "evidence_basis": action_plan["evidence"],
            "action_caveats": action_plan["caveats"],
        })

    result_df = pd.DataFrame(records).sort_values("priority_score", ascending=False).reset_index(drop=True)
    result_df["rank"] = result_df.index + 1
    return result_df


def generate_action_recommendation(
    station: str,
    zone: str,
    env: str,
    recent_mean: float,
    days_unhealthy: int,
    prob_risk: float,
    pred_interval: tuple[float, float],
    is_coastal: int
) -> dict:
    """
    Synthesizes actionable municipal advice grounded in verifiable observations.
    Avoids unverified claims of single-source attribution.
    """
    actions = []
    evidence = []
    caveats = []

    evidence.append(f"Recent 7-day exposure mean is {recent_mean:.1f} AQI with {days_unhealthy}/7 days exceeding Moderate threshold.")
    if prob_risk >= 0.60:
        evidence.append(f"Calibrated 24h probability of exceeding Unhealthy threshold (>200) is {prob_risk*100:.0f}%.")

    if recent_mean >= 180 or prob_risk >= 0.70:
        if "traffic" in env.lower() or "junction" in env.lower() or "highway" in env.lower():
            actions.append("Deploy BMC mobile anti-smog mist cannon along major express highway corridor during morning peak (07:30-10:30 IST); coordinate with Mumbai Traffic Police to mitigate bottleneck idling.")
            caveats.append("Road-dust suppression produces temporary local relief; does not eliminate tailpipe NOx/PM exhaust.")
        elif "industrial" in env.lower() or "ttc" in env.lower() or "midc" in env.lower():
            actions.append("Initiate MPCB spot inspections of boiler stack emissions and fugitive dust barriers in adjacent industrial belt; verify scrubber logs.")
            caveats.append("Station measurements capture mixed airshed background; individual factory culpability requires dedicated fence-line monitoring.")
        elif "dumping" in env.lower() or "deonar" in env.lower():
            actions.append("Deploy thermal imaging drone patrol across municipal solid waste landfill to detect smoldering subsurface combustion; activate methane misting.")
            caveats.append("Regional wind shifts can transport landfill smoke across Trombay and Chembur unpredictably.")
        else:
            actions.append("Issue ward-level public health advisory for vulnerable cohorts (elderly, pediatric, asthmatic); halt mechanized dry-sweeping in favor of vacuum/wet wash.")
            caveats.append("Health advisory compliance varies; impact cannot be measured from ambient monitors alone.")
    elif recent_mean >= 120 or prob_risk >= 0.40:
        actions.append("Inspect active construction and infrastructure redevelopment sites for mandatory 35-foot perimeter acoustic/dust barricades and conveyor tarping.")
        caveats.append("Construction dust constitutes coarse PM10; fine PM2.5 fractions remain influenced by combustion sources.")
    else:
        actions.append("Maintain baseline regulatory continuous monitoring; schedule routine optical zero-span calibration check.")
        caveats.append("Favorable current air quality is heavily sustained by sea-breeze ventilation; monitor wind forecast for seasonal stagnation.")

    return {
        "action": " ".join(actions),
        "evidence": " ".join(evidence),
        "caveats": " ".join(caveats)
    }


def simulate_capacity_constraint(priority_df: pd.DataFrame, capacity_n: int = 5) -> pd.DataFrame:
    """Simulates resource allocation under a budget constraint of N zones/week."""
    df = priority_df.copy()
    df["allocated_inspection"] = (df["rank"] <= capacity_n).astype(int)
    return df


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if not PREDICTIONS_PATH.exists():
        logging.error(f"Missing {PREDICTIONS_PATH}. Run src.models.train_evaluate first.")
        return

    df = pd.read_parquet(PREDICTIONS_PATH)
    priority_table = compute_station_priority_scores(df)

    out_path = PROCESSED_DIR / "mumbai_priority_rankings.parquet"
    out_csv = PROCESSED_DIR / "mumbai_priority_rankings.csv"
    priority_table.to_parquet(out_path, index=False)
    priority_table.to_csv(out_csv, index=False)

    print("\nPhase 4 Risk Prioritisation (ACT) Complete!")
    print(f"Top 5 Priority Zones for Municipal Intervention:")
    top_5 = priority_table[["rank", "station", "zone", "priority_score", "latest_aqi", "risk_tier"]].head(5)
    print(top_5.to_string(index=False))


if __name__ == "__main__":
    main()
