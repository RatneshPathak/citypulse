"""CityPulse: next-day PM2.5 forecast per station, with baselines, uncertainty and risk tier.

Run from the project root:
    python src/forecast.py

Reads  : data/citypulse_cleaned.csv  (hourly readings per station)
Writes : data/processed/metrics.json
         data/processed/test_predictions.csv
         data/processed/latest_forecast.csv
"""
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

DATA = "data/citypulse_cleaned.csv"
OUT = "data/processed"
POLLUTANTS = ["PM2.5", "PM10", "NO2", "CO"]  # SO2 skipped: ~32% missing
MIN_HOURS = 18   # a day needs at least this many valid hourly readings
MIN_DAYS = 90    # a station needs at least this many valid days
NOMINAL = 0.80   # interval is 10th-90th percentile of validation residuals

# CPCB-style PM2.5 (24h) categories. VERIFY these breakpoints against the CPCB
# AQI document and cite it in DATA_STATEMENT.md before presenting.
BINS = [-np.inf, 30, 60, 90, 120, 250, np.inf]
LABELS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
ACTIONS = {
    "Good": "No special action. Continue routine monitoring.",
    "Satisfactory": "Routine monitoring. Sensitive groups may take care.",
    "Moderate": "Watch closely. Consider advisory for sensitive groups.",
    "Poor": "Prioritise for inspection of local sources (dust, traffic, burning) and issue advisory.",
    "Very Poor": "High priority: targeted source control and public advisory; verify with expert review.",
    "Severe": "Highest priority: escalate to authorities; verify sensor and conditions.",
}


def tier(x):
    return pd.cut(x, bins=BINS, labels=LABELS)


def load_daily():
    df = pd.read_csv(DATA)
    df["ts"] = pd.to_datetime(df["From Date"], errors="coerce")
    df = df.dropna(subset=["ts"])
    df["date"] = df["ts"].dt.floor("D")
    g = df.groupby(["Station", "date"])[POLLUTANTS]
    mean = g.mean().where(g.count() >= MIN_HOURS)
    return mean.reset_index()


def build_features(daily):
    frames = []
    for st, g in daily.groupby("Station"):
        g = g.set_index("date").sort_index()
        g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="D"))
        g.index.name = "date"
        g["Station"] = st
        if g["PM2.5"].notna().sum() < MIN_DAYS:
            continue
        p = g["PM2.5"]
        f = pd.DataFrame(index=g.index)
        f["Station"] = st
        f["pm_today"] = p
        for k in range(1, 7):
            f[f"pm_lag{k}"] = p.shift(k)
        f["pm_roll7"] = p.rolling(7, min_periods=4).mean()
        f["pm10_today"] = g["PM10"]
        f["no2_today"] = g["NO2"]
        f["co_today"] = g["CO"]
        f["dow"] = f.index.dayofweek
        f["month"] = f.index.month
        f["target"] = p.shift(-1)  # PM2.5 tomorrow
        f["target_date"] = f.index + pd.Timedelta(days=1)
        frames.append(f.reset_index())
    feats = pd.concat(frames, ignore_index=True)
    feats["station_id"] = feats["Station"].astype("category").cat.codes
    return feats


def metrics(y, pred):
    return {
        "MAE": float(mean_absolute_error(y, pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y, pred))),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    daily = load_daily()
    feats = build_features(daily)
    feature_cols = (
        ["pm_today"] + [f"pm_lag{k}" for k in range(1, 7)]
        + ["pm_roll7", "pm10_today", "no2_today", "co_today", "dow", "month", "station_id"]
    )

    print("Stations used:", feats["Station"].nunique())
    print("Daily date range:", feats["date"].min().date(), "->", feats["date"].max().date())

    # Rows usable for training/evaluation
    labelled = feats.dropna(subset=["target", "pm_today"]).copy()

    # Chronological split by target date: 60% train / 20% validation / 20% test
    dates = np.sort(labelled["target_date"].unique())
    c1, c2 = dates[int(len(dates) * 0.6)], dates[int(len(dates) * 0.8)]
    train = labelled[labelled["target_date"] < c1]
    val = labelled[(labelled["target_date"] >= c1) & (labelled["target_date"] < c2)]
    test = labelled[labelled["target_date"] >= c2].copy()
    print(f"Train {len(train)} | Val {len(val)} | Test {len(test)} rows")
    print("Test period starts:", pd.Timestamp(c2).date())

    # Model trained on train only; residuals on validation give the uncertainty range
    model = HistGradientBoostingRegressor(random_state=42, max_iter=200, learning_rate=0.05)
    model.fit(train[feature_cols], train["target"])
    val_res = val["target"] - model.predict(val[feature_cols])
    q_lo, q_hi = np.nanpercentile(val_res, 10), np.nanpercentile(val_res, 90)

    # Test evaluation, on rows where both baselines exist (fair comparison)
    test["pred_model"] = model.predict(test[feature_cols])
    test["pred_persistence"] = test["pm_today"]          # tomorrow = today
    test["pred_weekly"] = test["pm_lag6"]                # same weekday last week
    fair = test.dropna(subset=["pred_persistence", "pred_weekly"]).copy()
    fair["lo"] = fair["pred_model"] + q_lo
    fair["hi"] = fair["pred_model"] + q_hi
    coverage = float(((fair["target"] >= fair["lo"]) & (fair["target"] <= fair["hi"])).mean())

    results = {
        "test_start": str(pd.Timestamp(c2).date()),
        "n_test_rows": int(len(fair)),
        "persistence_baseline": metrics(fair["target"], fair["pred_persistence"]),
        "same_weekday_baseline": metrics(fair["target"], fair["pred_weekly"]),
        "model": metrics(fair["target"], fair["pred_model"]),
        "interval_nominal": NOMINAL,
        "interval_empirical_coverage_on_test": coverage,
        "residual_quantiles_from_validation": {"p10": float(q_lo), "p90": float(q_hi)},
    }
    print("\nTEST RESULTS (lower is better):")
    for k in ("persistence_baseline", "same_weekday_baseline", "model"):
        print(f"  {k:24s} MAE={results[k]['MAE']:.2f}  RMSE={results[k]['RMSE']:.2f}")
    print(f"  80% interval coverage on test: {coverage:.2%} (nominal {NOMINAL:.0%})")

    per_station = (
        fair.assign(
            ae_model=(fair["target"] - fair["pred_model"]).abs(),
            ae_base=(fair["target"] - fair["pred_persistence"]).abs(),
        )
        .groupby("Station")[["ae_model", "ae_base"]].mean().round(2)
    )
    print("\nPer-station MAE (model vs persistence):\n", per_station)

    # Tier agreement: does the forecast land in the same category as the real value?
    same_tier = float((tier(fair["pred_model"]).astype(str) == tier(fair["target"]).astype(str)).mean())
    same_tier_base = float((tier(fair["pred_persistence"]).astype(str) == tier(fair["target"]).astype(str)).mean())
    results["tier_accuracy_model"] = same_tier
    results["tier_accuracy_persistence"] = same_tier_base
    print(f"\nCategory match: model {same_tier:.2%} vs persistence {same_tier_base:.2%}")

    fair.to_csv(f"{OUT}/test_predictions.csv", index=False)
    with open(f"{OUT}/metrics.json", "w") as fh:
        json.dump(results, fh, indent=2)

    # Final model on train+val, forecast for each station's most recent day
    final = HistGradientBoostingRegressor(random_state=42, max_iter=200, learning_rate=0.05)
    trval = pd.concat([train, val])
    final.fit(trval[feature_cols], trval["target"])
    last_global = feats["date"].max()
    latest = (
        feats.dropna(subset=["pm_today"]).sort_values("date").groupby("Station").tail(1).copy()
    )
    latest["forecast_pm25"] = final.predict(latest[feature_cols])
    latest["lo"] = (latest["forecast_pm25"] + q_lo).clip(lower=0)
    latest["hi"] = latest["forecast_pm25"] + q_hi
    latest["risk_tier"] = tier(latest["forecast_pm25"]).astype(str)
    latest["risk_tier_upper"] = tier(latest["hi"]).astype(str)
    latest["recommended_action"] = latest["risk_tier"].map(ACTIONS)
    latest["data_through"] = latest["date"].dt.date
    latest["stale_days"] = (last_global - latest["date"]).dt.days
    cols = ["Station", "data_through", "stale_days", "pm_today", "forecast_pm25", "lo", "hi",
            "risk_tier", "risk_tier_upper", "recommended_action"]
    latest[cols].round(1).to_csv(f"{OUT}/latest_forecast.csv", index=False)
    print("\nSaved: metrics.json, test_predictions.csv, latest_forecast.csv in", OUT)


if __name__ == "__main__":
    main()