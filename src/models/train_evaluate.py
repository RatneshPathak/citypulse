"""
Model Training, Baselines, and Chronological Evaluation — CityPulse: Mumbai

Strict Validation Design:
- Train Split: 2021-01-01 to 2022-12-31 (earlier 2 years)
- Test / Holdout Split: 2023-01-01 to 2023-12-31 (most recent full year)
- No random shuffling. No leakage of future statistics into train or test.

Baselines:
1. Persistence Baseline: Forecast(t) = AQI(t-1)
2. Seasonal Naive Baseline: Forecast(t) = AQI(t-7) (same day last week)

Candidate Models:
1. Ridge Regression (L2 regularised linear model)
2. Histogram Gradient Boosting Regressor
3. Quantile Gradient Boosting (p10, p90 for a nominal 80% interval)
4. Gradient Boosting Classifier for High Risk Event (AQI > 200)

Comprehensive Reporting:
- Regression Metrics: MAE, RMSE, R2, Skill Score vs Persistence
- Classification Metrics: Precision, Recall, F1, ROC-AUC, PR-AUC, Brier Score
- Calibration curves and empirical interval coverage check on 2023 holdout.
- Granular error breakdown per station and per season.
- Anomaly detection on prediction residuals.

Outputs:
- reports/figures/calibration_and_holdout.png
- reports/figures/prediction_intervals.png
- reports/figures/station_error_breakdown.png
- EVALUATION.md with exhaustive metrics tables
- data/processed/holdout_predictions.parquet for the Streamlit dashboard

Usage:
    python -m src.models.train_evaluate
"""
import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

FEATURES_PATH = Path("data/processed/mumbai_features_model_ready.parquet")
PROCESSED_DIR = Path("data/processed")
FIGURES_DIR = Path("reports/figures")
REPORTS_DIR = Path("reports")


def get_feature_columns() -> list[str]:
    """Define explicit numeric and categorical feature list."""
    return [
        "lag_1_aqi", "lag_2_aqi", "lag_3_aqi", "lag_7_aqi",
        "rolling_mean_7d", "rolling_std_7d", "rolling_min_7d", "rolling_max_7d", "trend_7d",
        "prior_day_temp_mean", "prior_day_humidity_mean", "prior_day_wind_speed_mean",
        "prior_day_wind_u_mean", "prior_day_wind_v_mean", "prior_day_rain_total_mm",
        "prior_day_pressure_mean", "prior_day_stagnation_index",
        "doy_sin", "doy_cos", "dow_sin", "dow_cos",
        "is_weekend", "is_monsoon", "is_winter", "is_diwali_window",
        "is_coastal", "latitude", "longitude"
    ]


def run_chronological_evaluation() -> dict:
    """Executes full chronological training, baseline comparisons, and diagnostics."""
    logging.info(f"Loading model features from {FEATURES_PATH}...")
    df = pd.read_parquet(FEATURES_PATH)
    df["date"] = pd.to_datetime(df["date"])

    feature_cols = [c for c in get_feature_columns() if c in df.columns]
    logging.info(f"Using {len(feature_cols)} predictor features: {feature_cols}")

    train_mask = (df["date"] >= "2021-01-01") & (df["date"] <= "2022-12-31")
    test_mask = (df["date"] >= "2023-01-01") & (df["date"] <= "2023-12-31")

    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()

    logging.info(f"Train period (2021-2022): {len(train_df):,} records")
    logging.info(f"Test period  (2023):       {len(test_df):,} records")

    X_train = train_df[feature_cols]
    y_train = train_df["target_next_day_aqi"]
    y_train_binary = train_df["target_next_day_unhealthy"]

    X_test = test_df[feature_cols]
    y_test = test_df["target_next_day_aqi"]
    y_test_binary = test_df["target_next_day_unhealthy"]

    logging.info("Computing baseline predictions on 2023 chronological holdout...")
    y_pred_persistence = test_df["lag_1_aqi"].values
    y_pred_seasonal_naive = test_df["lag_7_aqi"].fillna(test_df["lag_1_aqi"]).values

    y_pred_binary_persistence = (test_df["lag_1_aqi"] > 200).astype(int).values

    logging.info("Fitting Ridge Regression (L2 penalty)...")
    ridge_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=100.0, random_state=42))
    ])
    ridge_pipeline.fit(X_train, y_train)
    y_pred_ridge = ridge_pipeline.predict(X_test)

    logging.info("Fitting Gradient Boosting Regressor...")
    gb_reg = HistGradientBoostingRegressor(
        max_iter=150,
        learning_rate=0.06,
        max_depth=6,
        l2_regularization=1.0,
        random_state=42
    )
    gb_reg.fit(X_train, y_train)
    y_pred_gb = gb_reg.predict(X_test)

    logging.info("Fitting Quantile Gradient Boosters for 80% prediction intervals...")
    gb_q10 = HistGradientBoostingRegressor(loss="quantile", quantile=0.10, max_iter=120, max_depth=5, random_state=42)
    gb_q90 = HistGradientBoostingRegressor(loss="quantile", quantile=0.90, max_iter=120, max_depth=5, random_state=42)
    gb_q10.fit(X_train, y_train)
    gb_q90.fit(X_train, y_train)

    y_pred_p10 = gb_q10.predict(X_test)
    y_pred_p90 = gb_q90.predict(X_test)

    in_interval = (y_test.values >= y_pred_p10) & (y_test.values <= y_pred_p90)
    empirical_coverage = float(np.mean(in_interval)) * 100
    mean_interval_width = float(np.mean(y_pred_p90 - y_pred_p10))

    logging.info("Fitting Gradient Boosting Classifier for Unhealthy Risk (AQI > 200)...")
    gb_clf = HistGradientBoostingClassifier(
        max_iter=120,
        learning_rate=0.05,
        max_depth=5,
        class_weight="balanced",
        random_state=42
    )
    gb_clf.fit(X_train, y_train_binary)
    y_prob_gb = gb_clf.predict_proba(X_test)[:, 1]
    y_pred_binary_gb = (y_prob_gb >= 0.50).astype(int)

    log_reg_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=0.1, class_weight="balanced", random_state=42))
    ])
    log_reg_pipeline.fit(X_train, y_train_binary)
    y_prob_logreg = log_reg_pipeline.predict_proba(X_test)[:, 1]
    y_pred_binary_logreg = (y_prob_logreg >= 0.50).astype(int)

    def calc_reg_metrics(y_true, y_pred):
        return {
            "MAE": round(mean_absolute_error(y_true, y_pred), 2),
            "RMSE": round(np.sqrt(mean_squared_error(y_true, y_pred)), 2),
            "R2": round(r2_score(y_true, y_pred), 3),
        }

    metrics_persistence = calc_reg_metrics(y_test, y_pred_persistence)
    metrics_seasonal_naive = calc_reg_metrics(y_test, y_pred_seasonal_naive)
    metrics_ridge = calc_reg_metrics(y_test, y_pred_ridge)
    metrics_gb = calc_reg_metrics(y_test, y_pred_gb)

    skill_ridge = (1.0 - (metrics_ridge["MAE"] / metrics_persistence["MAE"])) * 100
    skill_gb = (1.0 - (metrics_gb["MAE"] / metrics_persistence["MAE"])) * 100

    metrics_persistence["Skill_vs_Persistence_%"] = 0.0
    metrics_seasonal_naive["Skill_vs_Persistence_%"] = round((1.0 - (metrics_seasonal_naive["MAE"] / metrics_persistence["MAE"])) * 100, 1)
    metrics_ridge["Skill_vs_Persistence_%"] = round(skill_ridge, 1)
    metrics_gb["Skill_vs_Persistence_%"] = round(skill_gb, 1)

    def calc_clf_metrics(y_true, y_pred, y_prob):
        return {
            "Precision": round(precision_score(y_true, y_pred, zero_division=0), 3),
            "Recall": round(recall_score(y_true, y_pred, zero_division=0), 3),
            "F1": round(f1_score(y_true, y_pred, zero_division=0), 3),
            "ROC_AUC": round(roc_auc_score(y_true, y_prob), 3) if y_prob is not None else np.nan,
            "PR_AUC": round(average_precision_score(y_true, y_prob), 3) if y_prob is not None else np.nan,
            "Brier_Score": round(brier_score_loss(y_true, y_prob), 4) if y_prob is not None else np.nan,
        }

    clf_persistence = calc_clf_metrics(y_test_binary, y_pred_binary_persistence, None)
    clf_logreg = calc_clf_metrics(y_test_binary, y_pred_binary_logreg, y_prob_logreg)
    clf_gb = calc_clf_metrics(y_test_binary, y_pred_binary_gb, y_prob_gb)

    test_df["pred_gb"] = y_pred_gb
    test_df["pred_p10"] = y_pred_p10
    test_df["pred_p90"] = y_pred_p90
    test_df["prob_unhealthy"] = y_prob_gb
    test_df["residual"] = test_df["target_next_day_aqi"] - test_df["pred_gb"]
    test_df["abs_residual"] = test_df["residual"].abs()

    anomaly_threshold = float(test_df["abs_residual"].quantile(0.98))
    test_df["is_anomaly"] = (test_df["abs_residual"] >= anomaly_threshold).astype(int)
    anomaly_events = test_df[test_df["is_anomaly"] == 1].sort_values("abs_residual", ascending=False)
    logging.info(f"Flagged {len(anomaly_events)} anomaly days (residual >= {anomaly_threshold:.1f} AQI units)")

    test_df["month"] = test_df["date"].dt.month
    def get_season(m):
        if m in [12, 1, 2]:
            return "Winter (Dec-Feb)"
        elif m in [3, 4, 5]:
            return "Pre-Monsoon / Summer"
        elif m in [6, 7, 8, 9]:
            return "Monsoon Washout"
        else:
            return "Post-Monsoon (Oct-Nov)"
    test_df["season"] = test_df["month"].apply(get_season)

    season_perf = []
    for s_name, grp in test_df.groupby("season"):
        p_mae = mean_absolute_error(grp["target_next_day_aqi"], grp["lag_1_aqi"])
        gb_mae = mean_absolute_error(grp["target_next_day_aqi"], grp["pred_gb"])
        season_perf.append({
            "season": s_name,
            "count": len(grp),
            "persistence_mae": round(p_mae, 1),
            "gb_mae": round(gb_mae, 1),
            "skill_%": round((1.0 - (gb_mae / p_mae)) * 100, 1),
            "mean_aqi": round(grp["target_next_day_aqi"].mean(), 1)
        })
    season_perf_df = pd.DataFrame(season_perf)

    station_perf = []
    for st_name, grp in test_df.groupby("canonical_station"):
        p_mae = mean_absolute_error(grp["target_next_day_aqi"], grp["lag_1_aqi"])
        gb_mae = mean_absolute_error(grp["target_next_day_aqi"], grp["pred_gb"])
        station_perf.append({
            "station": st_name,
            "zone": grp["zone"].iloc[0] if "zone" in grp else "MMR",
            "count": len(grp),
            "persistence_mae": round(p_mae, 1),
            "gb_mae": round(gb_mae, 1),
            "skill_%": round((1.0 - (gb_mae / p_mae)) * 100, 1),
            "mean_aqi": round(grp["target_next_day_aqi"].mean(), 1)
        })
    station_perf_df = pd.DataFrame(station_perf).sort_values("gb_mae")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={"height_ratios": [2, 1.2]})

    sample_station = "Bandra Kurla Complex" if "Bandra Kurla Complex" in test_df["canonical_station"].values else test_df["canonical_station"].iloc[0]
    st_sample = test_df[test_df["canonical_station"] == sample_station].sort_values("date")

    axes[0].plot(st_sample["date"], st_sample["target_next_day_aqi"], label="Actual AQI (Ground Truth)", color="#252525", linewidth=1.8)
    axes[0].plot(st_sample["date"], st_sample["pred_gb"], label="Gradient Boosting Forecast", color="#2b8cbe", linewidth=1.8, linestyle="--")
    axes[0].fill_between(st_sample["date"], st_sample["pred_p10"], st_sample["pred_p90"], color="#2b8cbe", alpha=0.20, label=f"80% Prediction Interval (Coverage: {empirical_coverage:.1f}%)")
    axes[0].axhline(200, color="#de2d26", linestyle=":", label="Unhealthy Regulatory Threshold (AQI > 200)")
    axes[0].set_title(f"Chronological Holdout Validation (2023): {sample_station}\nActual vs Forecast with 80% Quantile Prediction Interval", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("Daily Mean AQI")
    axes[0].legend(loc="upper right", frameon=True)

    prob_true, prob_pred = calibration_curve(y_test_binary, y_prob_gb, n_bins=8, strategy="uniform")
    axes[1].plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect Calibration")
    axes[1].plot(prob_pred, prob_true, marker="o", linewidth=2, color="#756bb1", label=f"Calibrated GB (Brier={clf_gb['Brier_Score']:.3f}, PR-AUC={clf_gb['PR_AUC']:.2f})")
    axes[1].set_title("Probability Calibration Curve: High Risk Unhealthy Event (AQI > 200)", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Predicted Probability")
    axes[1].set_ylabel("Observed Event Frequency")
    axes[1].legend(loc="upper left")

    plt.tight_layout()
    fig_holdout_path = FIGURES_DIR / "fig6_calibration_and_holdout.png"
    plt.savefig(fig_holdout_path, dpi=200)
    plt.close()

    fig, ax = plt.subplots(figsize=(12, 6))
    top_stations = station_perf_df.head(15)
    x = np.arange(len(top_stations))
    width = 0.35

    ax.bar(x - width/2, top_stations["persistence_mae"], width, label="Persistence Baseline MAE", color="#9ecae1")
    ax.bar(x + width/2, top_stations["gb_mae"], width, label="Gradient Boosting MAE", color="#3182bd")
    ax.set_title("Per-Station Holdout Performance (2023): Persistence vs Gradient Boosting MAE", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(top_stations["station"], rotation=30, ha="right")
    ax.set_ylabel("Mean Absolute Error (AQI Units)")
    ax.legend()
    plt.tight_layout()
    fig_station_path = FIGURES_DIR / "fig7_station_error_breakdown.png"
    plt.savefig(fig_station_path, dpi=200)
    plt.close()

    out_preds_path = PROCESSED_DIR / "holdout_predictions.parquet"
    test_df.to_parquet(out_preds_path, index=False)
    logging.info(f"Saved holdout predictions to {out_preds_path}")

    write_evaluation_document({
        "metrics_persistence": metrics_persistence,
        "metrics_seasonal_naive": metrics_seasonal_naive,
        "metrics_ridge": metrics_ridge,
        "metrics_gb": metrics_gb,
        "clf_persistence": clf_persistence,
        "clf_logreg": clf_logreg,
        "clf_gb": clf_gb,
        "empirical_coverage": empirical_coverage,
        "mean_interval_width": mean_interval_width,
        "season_perf_df": season_perf_df,
        "station_perf_df": station_perf_df,
        "anomaly_events": anomaly_events,
        "anomaly_threshold": anomaly_threshold,
    })

    return {
        "metrics_gb": metrics_gb,
        "metrics_persistence": metrics_persistence,
        "empirical_coverage": empirical_coverage,
        "clf_gb": clf_gb,
    }


def write_evaluation_document(results: dict):
    """Outputs the rigorous EVALUATION.md document."""
    logging.info("Writing comprehensive EVALUATION.md...")
    mp = results["metrics_persistence"]
    msn = results["metrics_seasonal_naive"]
    mr = results["metrics_ridge"]
    mgb = results["metrics_gb"]

    cp = results["clf_persistence"]
    clr = results["clf_logreg"]
    cgb = results["clf_gb"]
    gb_status = "Positive holdout skill" if mgb["MAE"] < mp["MAE"] else "Below persistence on MAE"
    assessment = (
        f"Gradient boosting beats persistence on MAE ({mgb['MAE']} vs {mp['MAE']})."
        if mgb["MAE"] < mp["MAE"]
        else f"Persistence has lower MAE ({mp['MAE']} vs {mgb['MAE']}); use it as the point-estimate benchmark."
    )

    content = f"""# Analytical Evaluation & Validation Report — CityPulse: Mumbai

Strict Chronological Holdout Design  
Train Set: 2021-01-01 to 2022-12-31 (earlier 24 months)  
Test Set: 2023-01-01 to 2023-12-31 (12-month forward holdout)  
No data shuffling, no target leakage, strictly decision-time feature sets.

---

## 1. Regression Benchmark: Next-Day AQI (Continuous)

Decision Rule: A model is considered valid for operational forecasting if and only if it achieves positive skill ($MAE_{{model}} < MAE_{{persistence}}$) on the forward chronological holdout.

| Model / Baseline | MAE (AQI Units) | RMSE | $R^2$ | Skill vs Persistence (%) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Persistence Baseline ($t-1$)** | **{mp['MAE']}** | {mp['RMSE']} | {mp['R2']} | 0.0% | Reference Baseline |
| **Seasonal Naive ($t-7$)** | **{msn['MAE']}** | {msn['RMSE']} | {msn['R2']} | {msn['Skill_vs_Persistence_%']:+.1f}% | Naive Reference |
| **Ridge Regression (L2 regularised)** | **{mr['MAE']}** | {mr['RMSE']} | {mr['R2']} | **{mr['Skill_vs_Persistence_%']:+.1f}%** | Candidate Linear |
| **Histogram Gradient Boosting** | **{mgb['MAE']}** | **{mgb['RMSE']}** | **{mgb['R2']}** | **{mgb['Skill_vs_Persistence_%']:+.1f}%** | {gb_status} |

### Decision Rule Assessment
- **Result:** {assessment} Skill score: **{mgb['Skill_vs_Persistence_%']:+.1f}%**.
- **Decision-time inputs:** Prior-day AQI and weather observations, calendar variables, station location, and rolling histories. The 2023 target-day reanalysis is excluded from model inputs.

---

## 2. Risk Classification Benchmark: High Risk Unhealthy Event (AQI > 200)

Intended Decision: Alerting municipal officers 24 hours prior to crossing regulatory "Poor" threshold.

| Model / Approach | Precision | Recall | F1 Score | PR-AUC | ROC-AUC | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Persistence State ($AQI_{{t-1}} > 200$)** | {cp['Precision']} | {cp['Recall']} | {cp['F1']} | N/A | N/A | N/A |
| **Regularised Logistic Regression** | {clr['Precision']} | {clr['Recall']} | {clr['F1']} | {clr['PR_AUC']} | {clr['ROC_AUC']} | {clr['Brier_Score']} |
| **Gradient Boosting Classifier** | **{cgb['Precision']}** | **{cgb['Recall']}** | **{cgb['F1']}** | **{cgb['PR_AUC']}** | **{cgb['ROC_AUC']}** | **{cgb['Brier_Score']}** |

![Calibration and Holdout](figures/fig6_calibration_and_holdout.png)

---

## 3. Uncertainty Quantification & Interval Coverage

- **Target Interval:** 80% Prediction Interval ($[p_{{10}}, p_{{90}}]$ via Quantile Gradient Boosting).
- **Empirical Holdout Coverage:** **{results['empirical_coverage']:.1f}%** (Nominal target: 80.0%).
- **Mean Interval Width:** **{results['mean_interval_width']:.1f} AQI units**.
- **Practical Translation:** The interval misses more observations than its nominal 80% target permits. Treat it as an exploratory range, not a calibrated 80% guarantee.

---

## 4. Sub-Group Performance: Seasonal Breakdown

| Season | Sample Days | Persistence MAE | Gradient Boosting MAE | Skill Score (%) | Mean AQI |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for _, r in results["season_perf_df"].iterrows():
        content += f"| **{r['season']}** | {int(r['count']):,} | {r['persistence_mae']} | **{r['gb_mae']}** | **{r['skill_%']:+.1f}%** | {r['mean_aqi']} |\n"

    content += f"""
---

## 5. Sub-Group Performance: Station Breakdown (Sample)

![Station Error Breakdown](figures/fig7_station_error_breakdown.png)

| Station Name | Zone | Persistence MAE | Gradient Boosting MAE | Skill Score (%) | Mean AQI |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for _, r in results["station_perf_df"].head(10).iterrows():
        content += f"| **{r['station']}** | {r['zone']} | {r['persistence_mae']} | **{r['gb_mae']}** | **{r['skill_%']:+.1f}%** | {r['mean_aqi']} |\n"

    content += f"""
---

## 6. Anomaly Detection & Diagnostic Audit

- **Anomaly Threshold:** Absolute forecast error $|y - \\hat{{y}}| \\ge {results['anomaly_threshold']:.1f}$ AQI units (Top 2% residual tail).
- **Top Flagged Anomalies:**
"""
    for _, r in results["anomaly_events"].head(5).iterrows():
        content += f"  - **{r['date'].strftime('%Y-%m-%d')} ({r['canonical_station']})**: Actual = {r['target_next_day_aqi']:.0f}, Forecast = {r['pred_gb']:.0f}, Residual = {r['residual']:+.0f}. Cause unverified; inspect station quality and local conditions.\n"

    content += """
---

## 7. What Could Make Our Conclusions Wrong?
1. **Unmodeled Emission Shocks:** Sudden localized emissions (e.g. episodic open waste burning in Deonar dumping ground, unannounced construction debris crushing, or traffic diversions) cannot be anticipated by regional meteorology and lag features alone.
2. **Lagged Sensor Reporting:** In live deployment, if telemetry from a station drops out for 6 hours, the persistence and lag features require real-time imputation, temporarily degrading forecast skill.
3. **Regional Transboundary Transport:** Continental agricultural residue burning or regional dust storms originating outside Maharashtra introduce air masses that regional Mumbai weather models cannot resolve without satellite optical depth (AOD) feeds.
"""
    with open(REPORTS_DIR / "EVALUATION.md", "w", encoding="utf-8") as f:
        f.write(content)
    metrics_summary = {
        "holdout_start": "2023-01-01",
        "holdout_end": "2023-12-31",
        "persistence": mp,
        "ridge": mr,
        "gradient_boosting": mgb,
        "classifier": cgb,
        "interval_coverage_pct": round(results["empirical_coverage"], 1),
        "interval_nominal_pct": 80,
    }
    with open(REPORTS_DIR / "evaluation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    logging.info(f"Wrote {REPORTS_DIR / 'EVALUATION.md'}")


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    res = run_chronological_evaluation()
    print("\nPhase 3 Analytical Modeling & Evaluation Complete!")
    print(f"Gradient Boosting MAE: {res['metrics_gb']['MAE']} (Persistence: {res['metrics_persistence']['MAE']})")
    print(f"Prediction Interval Empirical Coverage: {res['empirical_coverage']:.1f}%")
    print(f"Classification PR-AUC: {res['clf_gb']['PR_AUC']}")


if __name__ == "__main__":
    main()
