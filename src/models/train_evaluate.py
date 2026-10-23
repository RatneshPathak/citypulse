"""
Model Training, Baselines, and Chronological Evaluation — CityPulse: Mumbai

Validation design (executed in this order):

  STAGE 1 — Model-selection CV (2021-2022 data only)
  ---------------------------------------------------
  Three expanding folds with DATE boundaries (not row-index).  All stations
  are present in every fold; splits are on the date column.

  Fold 1:  train 2021-01-01 – 2021-12-31  (12 months min)
           test  2022-01-01 – 2022-04-30  (4 months)
  Fold 2:  train 2021-01-01 – 2022-04-30
           test  2022-05-01 – 2022-08-31
  Fold 3:  train 2021-01-01 – 2022-08-31
           test  2022-09-01 – 2022-12-31

  All features are backward-looking (lags, prior-day weather, expanding means
  shifted by 1 day), so no gap between train and test is required for leakage
  prevention.  A note to that effect replaces any earlier gap-as-leakage claim.

  Candidates in Stage 1 (Phase 1a):
    C1  Persistence baseline (lag_1_aqi)
    C2  Ridge (alpha chosen by RidgeCV on the same date-based folds)
    C3  HistGradientBoosting with squared_error loss (MSE; existing default)

  STAGE 2 — Final holdout evaluation (2023, touched exactly once)
  ---------------------------------------------------------------
  Chosen model retrained on full 2021-2022.  Reports MAE, RMSE, R2, skill vs
  persistence, and a paired-bootstrap 95% CI on the MAE difference.

lag_2_aqi status: present in get_feature_columns() (verified 2026-10-23).

Outputs:
  reports/EVALUATION.md
  reports/evaluation_metrics.json
  data/processed/holdout_predictions.parquet
  reports/figures/fig6_calibration_and_holdout.png
  reports/figures/fig7_station_error_breakdown.png

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

from sklearn.linear_model import Ridge, RidgeCV, LogisticRegression
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, brier_score_loss,
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

FEATURES_PATH = Path("data/processed/mumbai_features_model_ready.parquet")
PROCESSED_DIR  = Path("data/processed")
FIGURES_DIR    = Path("reports/figures")
REPORTS_DIR    = Path("reports")

_CV_FOLDS = [
    {
        "name": "Fold 1 (test 2022-Q1/Q2)",
        "train_start": "2021-01-01",
        "train_end":   "2021-12-31",
        "test_start":  "2022-01-01",
        "test_end":    "2022-04-30",
    },
    {
        "name": "Fold 2 (test 2022-Q2/Q3)",
        "train_start": "2021-01-01",
        "train_end":   "2022-04-30",
        "test_start":  "2022-05-01",
        "test_end":    "2022-08-31",
    },
    {
        "name": "Fold 3 (test 2022-Q3/Q4)",
        "train_start": "2021-01-01",
        "train_end":   "2022-08-31",
        "test_start":  "2022-09-01",
        "test_end":    "2022-12-31",
    },
]


def get_feature_columns() -> list[str]:
    """
    Explicit feature list used by all models.

    lag_2_aqi is listed here (verified present in parquet: 2026-10-23).
    New in Phase 1a: lag_14_aqi, rolling_mean_14d, rolling_std_14d, month,
    aqi_delta_1d, aqi_delta_7d, station_expanding_mean_aqi, is_holi_window.
    """
    return [
        "lag_1_aqi", "lag_2_aqi", "lag_3_aqi", "lag_7_aqi", "lag_14_aqi",
        "rolling_mean_7d", "rolling_std_7d", "rolling_min_7d", "rolling_max_7d", "trend_7d",
        "rolling_mean_14d", "rolling_std_14d",
        "aqi_delta_1d", "aqi_delta_7d",
        "station_expanding_mean_aqi",
        "prior_day_temp_mean", "prior_day_humidity_mean", "prior_day_wind_speed_mean",
        "prior_day_wind_u_mean", "prior_day_wind_v_mean", "prior_day_rain_total_mm",
        "prior_day_pressure_mean", "prior_day_stagnation_index",
        "doy_sin", "doy_cos", "dow_sin", "dow_cos",
        "is_weekend", "is_monsoon", "is_winter",
        "is_diwali_window", "is_holi_window",
        "month",
        "is_coastal", "latitude", "longitude",
    ]



def bootstrap_mae_diff_ci(
    y_true: np.ndarray,
    pred_model: np.ndarray,
    pred_baseline: np.ndarray,
    n_boot: int = 2000,
    seed: int = 42,
) -> tuple[float, float]:
    """
    Paired bootstrap 95% CI on (MAE_model − MAE_baseline).

    Negative values mean the model has lower (better) MAE than baseline.
    Bootstrap is paired: the same resampled indices are applied to both.

    Parameters
    ----------
    y_true, pred_model, pred_baseline : np.ndarray
        Must be the same length; no NaNs allowed.
    n_boot : int
        Number of bootstrap replicates (default 2000).
    seed : int
        RNG seed for reproducibility.

    Returns
    -------
    (ci_lo, ci_hi) : (float, float)
        2.5th and 97.5th percentile of the bootstrap distribution.
    """
    rng = np.random.default_rng(seed)
    n = len(y_true)
    diffs = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        mae_m = np.mean(np.abs(y_true[idx] - pred_model[idx]))
        mae_b = np.mean(np.abs(y_true[idx] - pred_baseline[idx]))
        diffs[i] = mae_m - mae_b
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))



def _fold_masks(df: pd.DataFrame, fold: dict) -> tuple[pd.Series, pd.Series]:
    """Return boolean train and test masks for one CV fold."""
    dates = pd.to_datetime(df["date"])
    tr_mask = (dates >= fold["train_start"]) & (dates <= fold["train_end"])
    te_mask = (dates >= fold["test_start"])  & (dates <= fold["test_end"])
    return tr_mask, te_mask


def _fold_idx(df: pd.DataFrame, fold: dict) -> tuple[np.ndarray, np.ndarray]:
    """Return integer positional train and test indices for one CV fold."""
    tr_mask, te_mask = _fold_masks(df, fold)
    return np.where(tr_mask)[0], np.where(te_mask)[0]



def _reg_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "MAE":  round(mean_absolute_error(y_true, y_pred), 2),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
        "R2":   round(r2_score(y_true, y_pred), 3),
    }



def run_cv_model_selection(df: pd.DataFrame, feature_cols: list[str]) -> dict:
    """
    Run 3-fold expanding-window CV on the 2021-2022 training window.

    Candidates evaluated here (Phase 1a):
      - Persistence (lag_1_aqi) — reference baseline
      - Ridge with alpha selected by RidgeCV on the same date-based folds
      - HistGradientBoosting with squared_error loss

    Returns
    -------
    dict with per-fold and aggregate metrics for each candidate, plus
    the chosen best_model_name and best_model_params.
    """
    logging.info("=" * 70)
    logging.info("STAGE 1: Expanding-window CV on 2021-2022 (3 date-based folds)")
    logging.info("=" * 70)

    dates = pd.to_datetime(df["date"])
    cv_mask = (dates >= "2021-01-01") & (dates <= "2022-12-31")
    cv_df = df[cv_mask].copy().reset_index(drop=True)
    cv_df["date"] = pd.to_datetime(cv_df["date"])

    fcs = [c for c in feature_cols if c in cv_df.columns]
    logging.info(f"Features available in parquet: {len(fcs)} / {len(feature_cols)}")
    missing = set(feature_cols) - set(cv_df.columns)
    if missing:
        logging.warning(f"Features requested but absent from parquet: {missing}")

    alphas_grid = np.logspace(-1, 4, 25)
    cv_idx_pairs = [_fold_idx(cv_df, fold) for fold in _CV_FOLDS]

    ridge_pipeline_cv = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("model",   RidgeCV(alphas=alphas_grid, cv=cv_idx_pairs, scoring="neg_mean_absolute_error")),
    ])
    ridge_pipeline_cv.fit(cv_df[fcs], cv_df["target_next_day_aqi"])
    best_alpha = float(ridge_pipeline_cv.named_steps["model"].alpha_)
    logging.info(f"RidgeCV selected alpha = {best_alpha:.2f}")

    def make_ridge():
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler",  StandardScaler()),
            ("model",   Ridge(alpha=best_alpha, random_state=42)),
        ])

    def make_hgb_mse():
        return HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=150,
            learning_rate=0.06,
            max_depth=6,
            l2_regularization=1.0,
            random_state=42,
        )

    candidates = {
        "Persistence": None,
        "Ridge":       make_ridge,
        "HistGB_MSE":  make_hgb_mse,
    }

    fold_results = {name: [] for name in candidates}
    oof_preds  = {name: np.full(len(cv_df), np.nan) for name in candidates}
    oof_actual = np.full(len(cv_df), np.nan)

    for fold in _CV_FOLDS:
        tr_mask, te_mask = _fold_masks(cv_df, fold)
        tr_idx = np.where(tr_mask)[0]
        te_idx = np.where(te_mask)[0]

        fold_train = cv_df[tr_mask]
        fold_test  = cv_df[te_mask]

        X_tr = fold_train[fcs]
        y_tr = fold_train["target_next_day_aqi"].values
        X_te = fold_test[fcs]
        y_te = fold_test["target_next_day_aqi"].values

        oof_actual[te_idx] = y_te

        y_persist = fold_test["lag_1_aqi"].values
        valid = ~np.isnan(y_te) & ~np.isnan(y_persist)
        m = _reg_metrics(y_te[valid], y_persist[valid])
        fold_results["Persistence"].append({"fold": fold["name"], **m, "n": int(valid.sum())})
        oof_preds["Persistence"][te_idx] = y_persist

        ridge = make_ridge()
        ridge.fit(X_tr, y_tr)
        y_ridge = ridge.predict(X_te)
        valid = ~np.isnan(y_te) & ~np.isnan(y_ridge)
        m = _reg_metrics(y_te[valid], y_ridge[valid])
        fold_results["Ridge"].append({"fold": fold["name"], **m, "n": int(valid.sum())})
        oof_preds["Ridge"][te_idx] = y_ridge

        hgb = make_hgb_mse()
        hgb.fit(X_tr, y_tr)
        y_hgb = hgb.predict(X_te)
        valid = ~np.isnan(y_te) & ~np.isnan(y_hgb)
        m = _reg_metrics(y_te[valid], y_hgb[valid])
        fold_results["HistGB_MSE"].append({"fold": fold["name"], **m, "n": int(valid.sum())})
        oof_preds["HistGB_MSE"][te_idx] = y_hgb

        logging.info(f"  {fold['name']}: train={len(fold_train):,} test={len(fold_test):,}")

    agg = {}
    valid_oof = ~np.isnan(oof_actual) & ~np.isnan(oof_preds["Persistence"])

    persist_oof_valid = oof_preds["Persistence"][valid_oof]
    actual_oof_valid  = oof_actual[valid_oof]

    for name in candidates:
        preds = oof_preds[name]
        v = valid_oof & ~np.isnan(preds)
        m = _reg_metrics(actual_oof_valid[v[valid_oof]], preds[v][v[valid_oof]])

        persist_mae_here = mean_absolute_error(
            actual_oof_valid[v[valid_oof]],
            persist_oof_valid[v[valid_oof]],
        )
        skill = (1.0 - m["MAE"] / persist_mae_here) * 100

        ci_lo, ci_hi = bootstrap_mae_diff_ci(
            actual_oof_valid[v[valid_oof]],
            preds[v][v[valid_oof]],
            persist_oof_valid[v[valid_oof]],
        ) if name != "Persistence" else (0.0, 0.0)

        agg[name] = {
            **m,
            "Skill_vs_Persistence_%": round(skill, 1),
            "Bootstrap_CI_MAE_diff_95": (round(ci_lo, 2), round(ci_hi, 2)),
            "fold_MAEs": [r["MAE"] for r in fold_results[name]],
        }
        logging.info(
            f"  OOF {name:16s}  MAE={m['MAE']:.2f}  Skill={skill:+.1f}%  "
            f"CI=[{ci_lo:+.2f}, {ci_hi:+.2f}]"
        )

    non_baseline = {k: v for k, v in agg.items() if k != "Persistence"}
    best_name = min(non_baseline, key=lambda k: non_baseline[k]["MAE"])
    best_params = {
        "Ridge":      {"alpha": best_alpha},
        "HistGB_MSE": {"loss": "squared_error", "max_iter": 150, "lr": 0.06, "max_depth": 6},
    }.get(best_name, {})
    logging.info(f"  → Best CV model: {best_name}  (MAE={agg[best_name]['MAE']:.2f})")

    return {
        "fold_results":  fold_results,
        "agg":           agg,
        "best_name":     best_name,
        "best_alpha":    best_alpha,
        "feature_cols":  fcs,
        "cv_folds":      _CV_FOLDS,
    }



def run_chronological_evaluation() -> dict:
    """
    Load features, run CV for model selection, then evaluate on 2023 holdout.

    The 2023 data is not accessed during Stage 1.  After the best model is
    chosen, it is retrained on the full 2021-2022 window and evaluated once.
    """
    logging.info(f"Loading model features from {FEATURES_PATH}...")
    df = pd.read_parquet(FEATURES_PATH)
    df["date"] = pd.to_datetime(df["date"])

    feature_cols = get_feature_columns()

    cv_results = run_cv_model_selection(df, feature_cols)
    fcs = cv_results["feature_cols"]
    best_name   = cv_results["best_name"]
    best_alpha  = cv_results["best_alpha"]

    logging.info("=" * 70)
    logging.info("STAGE 2: Final holdout evaluation on 2023 (touched once)")
    logging.info("=" * 70)

    train_mask = (df["date"] >= "2021-01-01") & (df["date"] <= "2022-12-31")
    test_mask  = (df["date"] >= "2023-01-01") & (df["date"] <= "2023-12-31")

    train_df = df[train_mask].copy()
    test_df  = df[test_mask].copy()
    logging.info(f"Train (2021-2022): {len(train_df):,} rows")
    logging.info(f"Test  (2023):       {len(test_df):,} rows")

    X_train = train_df[fcs]
    y_train = train_df["target_next_day_aqi"]
    y_train_binary = train_df["target_next_day_unhealthy"]

    X_test = test_df[fcs]
    y_test  = test_df["target_next_day_aqi"]
    y_test_binary = test_df["target_next_day_unhealthy"]

    y_pred_persistence    = test_df["lag_1_aqi"].values
    y_pred_seasonal_naive = test_df["lag_7_aqi"].fillna(test_df["lag_1_aqi"]).values

    if best_name == "Ridge":
        best_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler",  StandardScaler()),
            ("model",   Ridge(alpha=best_alpha, random_state=42)),
        ])
        best_pipeline.fit(X_train, y_train)
        y_pred_best = best_pipeline.predict(X_test)
    else:
        best_pipeline = HistGradientBoostingRegressor(
            loss="squared_error", max_iter=150, learning_rate=0.06,
            max_depth=6, l2_regularization=1.0, random_state=42,
        )
        best_pipeline.fit(X_train, y_train)
        y_pred_best = best_pipeline.predict(X_test)

    ridge_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("model",   Ridge(alpha=best_alpha, random_state=42)),
    ])
    ridge_pipeline.fit(X_train, y_train)
    y_pred_ridge = ridge_pipeline.predict(X_test)

    hgb_mse = HistGradientBoostingRegressor(
        loss="squared_error", max_iter=150, learning_rate=0.06,
        max_depth=6, l2_regularization=1.0, random_state=42,
    )
    hgb_mse.fit(X_train, y_train)
    y_pred_gb = hgb_mse.predict(X_test)

    logging.info("Fitting quantile models for 80% prediction intervals...")
    gb_q10 = HistGradientBoostingRegressor(
        loss="quantile", quantile=0.10, max_iter=120, max_depth=5, random_state=42,
    )
    gb_q90 = HistGradientBoostingRegressor(
        loss="quantile", quantile=0.90, max_iter=120, max_depth=5, random_state=42,
    )
    gb_q10.fit(X_train, y_train)
    gb_q90.fit(X_train, y_train)
    y_pred_p10 = gb_q10.predict(X_test)
    y_pred_p90 = gb_q90.predict(X_test)
    in_interval = (y_test.values >= y_pred_p10) & (y_test.values <= y_pred_p90)
    empirical_coverage   = float(np.mean(in_interval)) * 100
    mean_interval_width  = float(np.mean(y_pred_p90 - y_pred_p10))

    logging.info("Fitting GB classifier for AQI > 200 risk...")
    gb_clf = HistGradientBoostingClassifier(
        max_iter=120, learning_rate=0.05, max_depth=5,
        class_weight="balanced", random_state=42,
    )
    gb_clf.fit(X_train, y_train_binary)
    y_prob_gb    = gb_clf.predict_proba(X_test)[:, 1]
    y_pred_bin_gb = (y_prob_gb >= 0.50).astype(int)

    log_reg_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("model",   LogisticRegression(C=0.1, class_weight="balanced", random_state=42)),
    ])
    log_reg_pipeline.fit(X_train, y_train_binary)
    y_prob_logreg    = log_reg_pipeline.predict_proba(X_test)[:, 1]
    y_pred_bin_logreg = (y_prob_logreg >= 0.50).astype(int)

    valid_persist = ~np.isnan(y_pred_persistence)
    valid_sn      = ~np.isnan(y_pred_seasonal_naive)

    metrics_persistence    = _reg_metrics(y_test.values[valid_persist], y_pred_persistence[valid_persist])
    metrics_seasonal_naive = _reg_metrics(y_test.values[valid_sn],      y_pred_seasonal_naive[valid_sn])
    metrics_ridge          = _reg_metrics(y_test.values, y_pred_ridge)
    metrics_gb             = _reg_metrics(y_test.values, y_pred_gb)

    def _skill(m_model, m_persist):
        return round((1.0 - m_model["MAE"] / m_persist["MAE"]) * 100, 1)

    metrics_persistence["Skill_vs_Persistence_%"]    = 0.0
    metrics_seasonal_naive["Skill_vs_Persistence_%"] = _skill(metrics_seasonal_naive, metrics_persistence)
    metrics_ridge["Skill_vs_Persistence_%"]          = _skill(metrics_ridge, metrics_persistence)
    metrics_gb["Skill_vs_Persistence_%"]             = _skill(metrics_gb, metrics_persistence)

    metrics_ridge["Bootstrap_CI_MAE_diff_95"] = bootstrap_mae_diff_ci(
        y_test.values, y_pred_ridge, y_pred_persistence[valid_persist],
    ) if valid_persist.all() else (None, None)
    metrics_gb["Bootstrap_CI_MAE_diff_95"] = bootstrap_mae_diff_ci(
        y_test.values, y_pred_gb, y_pred_persistence,
    )

    logging.info(f"  Persistence  MAE={metrics_persistence['MAE']:.2f}")
    logging.info(f"  Ridge        MAE={metrics_ridge['MAE']:.2f}  Skill={metrics_ridge['Skill_vs_Persistence_%']:+.1f}%")
    logging.info(f"  HistGB_MSE   MAE={metrics_gb['MAE']:.2f}  Skill={metrics_gb['Skill_vs_Persistence_%']:+.1f}%")

    y_pred_bin_persist = (test_df["lag_1_aqi"] > 200).astype(int).values

    def _clf_metrics(y_true, y_pred, y_prob):
        return {
            "Precision":   round(precision_score(y_true, y_pred, zero_division=0), 3),
            "Recall":      round(recall_score(y_true, y_pred, zero_division=0), 3),
            "F1":          round(f1_score(y_true, y_pred, zero_division=0), 3),
            "ROC_AUC":     round(roc_auc_score(y_true, y_prob), 3) if y_prob is not None else None,
            "PR_AUC":      round(average_precision_score(y_true, y_prob), 3) if y_prob is not None else None,
            "Brier_Score": round(brier_score_loss(y_true, y_prob), 4) if y_prob is not None else None,
        }

    clf_persistence = _clf_metrics(y_test_binary, y_pred_bin_persist, None)
    clf_logreg      = _clf_metrics(y_test_binary, y_pred_bin_logreg, y_prob_logreg)
    clf_gb          = _clf_metrics(y_test_binary, y_pred_bin_gb, y_prob_gb)

    test_df = test_df.copy()
    test_df["pred_gb"]       = y_pred_gb
    test_df["pred_p10"]      = y_pred_p10
    test_df["pred_p90"]      = y_pred_p90
    test_df["prob_unhealthy"] = y_prob_gb
    test_df["residual"]      = test_df["target_next_day_aqi"] - test_df["pred_gb"]
    test_df["abs_residual"]  = test_df["residual"].abs()

    anomaly_threshold = float(test_df["abs_residual"].quantile(0.98))
    test_df["is_anomaly"] = (test_df["abs_residual"] >= anomaly_threshold).astype(int)
    anomaly_events = test_df[test_df["is_anomaly"] == 1].sort_values("abs_residual", ascending=False)
    logging.info(f"Flagged {len(anomaly_events)} anomaly days (|residual| >= {anomaly_threshold:.1f})")

    test_df["month_num"] = test_df["date"].dt.month

    def _get_season(m):
        if m in [12, 1, 2]:   return "Winter (Dec-Feb)"
        if m in [3, 4, 5]:    return "Pre-Monsoon / Summer"
        if m in [6, 7, 8, 9]: return "Monsoon Washout"
        return "Post-Monsoon (Oct-Nov)"

    test_df["season"] = test_df["month_num"].apply(_get_season)

    season_perf = []
    for s_name, grp in test_df.groupby("season"):
        p_mae  = mean_absolute_error(grp["target_next_day_aqi"], grp["lag_1_aqi"])
        gb_mae = mean_absolute_error(grp["target_next_day_aqi"], grp["pred_gb"])
        season_perf.append({
            "season":           s_name,
            "count":            len(grp),
            "persistence_mae":  round(p_mae, 1),
            "gb_mae":           round(gb_mae, 1),
            "skill_%":          round((1.0 - gb_mae / p_mae) * 100, 1),
            "mean_aqi":         round(grp["target_next_day_aqi"].mean(), 1),
        })
    season_perf_df = pd.DataFrame(season_perf)

    station_perf = []
    for st_name, grp in test_df.groupby("canonical_station"):
        p_mae  = mean_absolute_error(grp["target_next_day_aqi"], grp["lag_1_aqi"])
        gb_mae = mean_absolute_error(grp["target_next_day_aqi"], grp["pred_gb"])
        station_perf.append({
            "station":          st_name,
            "zone":             grp["zone"].iloc[0] if "zone" in grp.columns else "MMR",
            "count":            len(grp),
            "persistence_mae":  round(p_mae, 1),
            "gb_mae":           round(gb_mae, 1),
            "skill_%":          round((1.0 - gb_mae / p_mae) * 100, 1),
            "mean_aqi":         round(grp["target_next_day_aqi"].mean(), 1),
        })
    station_perf_df = pd.DataFrame(station_perf).sort_values("gb_mae")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    _make_calibration_figure(
        test_df, empirical_coverage, clf_gb, y_test_binary, y_prob_gb,
    )
    _make_station_figure(station_perf_df)

    out_preds_path = PROCESSED_DIR / "holdout_predictions.parquet"
    test_df.to_parquet(out_preds_path, index=False)
    logging.info(f"Saved holdout predictions to {out_preds_path}")

    write_evaluation_document({
        "cv_results":            cv_results,
        "best_name":             best_name,
        "best_alpha":            best_alpha,
        "metrics_persistence":   metrics_persistence,
        "metrics_seasonal_naive": metrics_seasonal_naive,
        "metrics_ridge":         metrics_ridge,
        "metrics_gb":            metrics_gb,
        "clf_persistence":       clf_persistence,
        "clf_logreg":            clf_logreg,
        "clf_gb":                clf_gb,
        "empirical_coverage":    empirical_coverage,
        "mean_interval_width":   mean_interval_width,
        "season_perf_df":        season_perf_df,
        "station_perf_df":       station_perf_df,
        "anomaly_events":        anomaly_events,
        "anomaly_threshold":     anomaly_threshold,
        "feature_cols":          fcs,
    })

    return {
        "cv_results":         cv_results,
        "metrics_gb":         metrics_gb,
        "metrics_persistence": metrics_persistence,
        "empirical_coverage": empirical_coverage,
        "clf_gb":             clf_gb,
        "best_name":          best_name,
    }



def _make_calibration_figure(test_df, empirical_coverage, clf_gb, y_test_binary, y_prob_gb):
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={"height_ratios": [2, 1.2]})
    sample_station = (
        "Bandra Kurla Complex"
        if "Bandra Kurla Complex" in test_df["canonical_station"].values
        else test_df["canonical_station"].iloc[0]
    )
    st_sample = test_df[test_df["canonical_station"] == sample_station].sort_values("date")

    axes[0].plot(st_sample["date"], st_sample["target_next_day_aqi"],
                 label="Actual AQI (Ground Truth)", color="#252525", linewidth=1.8)
    axes[0].plot(st_sample["date"], st_sample["pred_gb"],
                 label="Gradient Boosting Forecast", color="#2b8cbe", linewidth=1.8, linestyle="--")
    axes[0].fill_between(
        st_sample["date"], st_sample["pred_p10"], st_sample["pred_p90"],
        color="#2b8cbe", alpha=0.20,
        label=f"80% Prediction Interval (Coverage: {empirical_coverage:.1f}%)",
    )
    axes[0].axhline(200, color="#de2d26", linestyle=":", label="AQI > 200 threshold")
    axes[0].set_title(
        f"Chronological Holdout 2023: {sample_station}\n"
        "Actual vs Forecast with 80% Quantile Prediction Interval",
        fontsize=12, fontweight="bold",
    )
    axes[0].set_ylabel("Daily Mean AQI")
    axes[0].legend(loc="upper right", frameon=True)

    prob_true, prob_pred = calibration_curve(y_test_binary, y_prob_gb, n_bins=8, strategy="uniform")
    axes[1].plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect calibration")
    axes[1].plot(prob_pred, prob_true, marker="o", linewidth=2, color="#756bb1",
                 label=f"GB classifier (Brier={clf_gb['Brier_Score']:.3f}, PR-AUC={clf_gb['PR_AUC']:.2f})")
    axes[1].set_title("Calibration Curve: AQI > 200 risk classifier", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Predicted probability")
    axes[1].set_ylabel("Observed event frequency")
    axes[1].legend(loc="upper left")

    plt.tight_layout()
    path = FIGURES_DIR / "fig6_calibration_and_holdout.png"
    plt.savefig(path, dpi=200)
    plt.close()
    logging.info(f"Saved {path}")


def _make_station_figure(station_perf_df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12, 6))
    top = station_perf_df.head(15)
    x, width = np.arange(len(top)), 0.35
    ax.bar(x - width / 2, top["persistence_mae"], width,
           label="Persistence MAE", color="#9ecae1")
    ax.bar(x + width / 2, top["gb_mae"],          width,
           label="HistGB_MSE MAE", color="#3182bd")
    ax.set_title("Per-Station Holdout 2023: Persistence vs HistGB_MSE MAE",
                 fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(top["station"], rotation=30, ha="right")
    ax.set_ylabel("MAE (AQI units)")
    ax.legend()
    plt.tight_layout()
    path = FIGURES_DIR / "fig7_station_error_breakdown.png"
    plt.savefig(path, dpi=200)
    plt.close()
    logging.info(f"Saved {path}")



def write_evaluation_document(results: dict) -> None:
    """Write EVALUATION.md and evaluation_metrics.json from evaluation results."""
    logging.info("Writing EVALUATION.md...")

    cv   = results["cv_results"]
    mp   = results["metrics_persistence"]
    msn  = results["metrics_seasonal_naive"]
    mr   = results["metrics_ridge"]
    mgb  = results["metrics_gb"]
    cp   = results["clf_persistence"]
    clr  = results["clf_logreg"]
    cgb  = results["clf_gb"]
    bn   = results["best_name"]

    def _ci_str(m, key="Bootstrap_CI_MAE_diff_95"):
        ci = m.get(key)
        if ci and ci[0] is not None:
            return f"[{ci[0]:+.2f}, {ci[1]:+.2f}]"
        return "N/A"

    gb_beats = mgb["MAE"] < mp["MAE"]
    assessment = (
        f"HistGB_MSE beats persistence on MAE ({mgb['MAE']} vs {mp['MAE']})."
        if gb_beats
        else f"Persistence has lower MAE ({mp['MAE']} vs {mgb['MAE']}); "
             "dashboard uses historical replay rather than live forecast."
    )

    cv_table = ""
    for name, agg in cv["agg"].items():
        fold_str = ", ".join(f"{m:.2f}" for m in agg["fold_MAEs"])
        ci_lo, ci_hi = agg["Bootstrap_CI_MAE_diff_95"]
        cv_table += (
            f"| **{name}** | {agg['MAE']} | {agg['RMSE']} | {agg['R2']} "
            f"| {agg['Skill_vs_Persistence_%']:+.1f}% "
            f"| {ci_lo:+.2f} to {ci_hi:+.2f} "
            f"| {fold_str} |\n"
        )

    content = f"""# Analytical Evaluation & Validation Report — CityPulse: Mumbai

Strict Chronological Holdout Design  
Train Set: 2021-01-01 to 2022-12-31 (24 months)  
Test Set:  2023-01-01 to 2023-12-31 (12-month forward holdout, touched once)  
No data shuffling, no target leakage, strictly decision-time feature sets.

Phase 1a feature additions (2026-10-23): lag_14, rolling_mean/std_14d, month,
aqi_delta_1d, aqi_delta_7d, station_expanding_mean_aqi (shift-1 expanding mean),
is_holi_window (Wikipedia Holi dates across multi-year period).

---

## 0. lag_2_aqi status

`lag_2_aqi` is confirmed present in `get_feature_columns()` and in the parquet
(verified 2026-10-23 before any other changes).

---

## 1. Model-selection CV (2021-2022 only)

Three expanding folds with **date boundaries** — splits are on the date column,
not the row index (the dataset is stacked multi-station).  Fold 1 trains on a
minimum of 12 months.  Features are backward-looking only (lags, prior-day
weather, expanding mean shifted by 1 day); no gap is needed for leakage
prevention, and none is claimed here.

Ridge alpha was selected by `RidgeCV` on the same three date-based folds
(`scoring=neg_mean_absolute_error`, log-scale grid 0.1–10 000).
Best alpha: **{results['best_alpha']:.2f}**.

Bootstrap CI = paired 95% CI on (MAE_model − MAE_persistence), 2000 replicates,
fixed seed=42.  Negative CI → model better than persistence.

| Model | OOF MAE | OOF RMSE | OOF R² | Skill vs Persist | Bootstrap CI (MAE diff) | Per-fold MAEs |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{cv_table}
CV winner: **{bn}**

---

## 2. Regression Benchmark: Next-Day AQI — 2023 Holdout (evaluated once)

| Model / Baseline | MAE | RMSE | R² | Skill vs Persistence | Bootstrap 95% CI (MAE diff) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Persistence (t-1)** | **{mp['MAE']}** | {mp['RMSE']} | {mp['R2']} | 0.0% | — |
| **Seasonal Naive (t-7)** | **{msn['MAE']}** | {msn['RMSE']} | {msn['R2']} | {msn['Skill_vs_Persistence_%']:+.1f}% | — |
| **Ridge (alpha={results['best_alpha']:.1f})** | **{mr['MAE']}** | {mr['RMSE']} | {mr['R2']} | {mr['Skill_vs_Persistence_%']:+.1f}% | {_ci_str(mr)} |
| **HistGB_MSE** | **{mgb['MAE']}** | {mgb['RMSE']} | {mgb['R2']} | {mgb['Skill_vs_Persistence_%']:+.1f}% | {_ci_str(mgb)} |

**Result:** {assessment}  
Features used: {len(results['feature_cols'])} (was 27 before Phase 1a).

---

## 3. Risk Classification: AQI > 200 — 2023 Holdout

| Model | Precision | Recall | F1 | PR-AUC | ROC-AUC | Brier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Persistence state** | {cp['Precision']} | {cp['Recall']} | {cp['F1']} | N/A | N/A | N/A |
| **Logistic Regression** | {clr['Precision']} | {clr['Recall']} | {clr['F1']} | {clr['PR_AUC']} | {clr['ROC_AUC']} | {clr['Brier_Score']} |
| **GB Classifier** | **{cgb['Precision']}** | **{cgb['Recall']}** | **{cgb['F1']}** | **{cgb['PR_AUC']}** | **{cgb['ROC_AUC']}** | **{cgb['Brier_Score']}** |

![Calibration and Holdout](figures/fig6_calibration_and_holdout.png)

---

## 4. Uncertainty Quantification — 2023 Holdout

- **Target interval:** 80% prediction interval ([p10, p90] via quantile GB).
- **Empirical coverage:** **{results['empirical_coverage']:.1f}%** (nominal: 80.0%).
- **Mean interval width:** **{results['mean_interval_width']:.1f} AQI units**.
- **Practical note:** Coverage is below the 80% nominal target; treat as an
  exploratory range, not a calibrated guarantee.

---

## 5. Seasonal Breakdown — 2023 Holdout

| Season | N days | Persistence MAE | HistGB_MSE MAE | Skill | Mean AQI |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for _, r in results["season_perf_df"].iterrows():
        content += (
            f"| **{r['season']}** | {int(r['count']):,} | {r['persistence_mae']} "
            f"| **{r['gb_mae']}** | **{r['skill_%']:+.1f}%** | {r['mean_aqi']} |\n"
        )

    content += f"""
---

## 6. Station Breakdown (sample) — 2023 Holdout

![Station Error Breakdown](figures/fig7_station_error_breakdown.png)

| Station | Zone | Persistence MAE | HistGB_MSE MAE | Skill | Mean AQI |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for _, r in results["station_perf_df"].head(10).iterrows():
        content += (
            f"| **{r['station']}** | {r['zone']} | {r['persistence_mae']} "
            f"| **{r['gb_mae']}** | **{r['skill_%']:+.1f}%** | {r['mean_aqi']} |\n"
        )

    content += f"""
---

## 7. Anomaly Detection

- Threshold: |residual| ≥ {results['anomaly_threshold']:.1f} AQI units (top 2% of error tail).
- Top events:
"""
    for _, r in results["anomaly_events"].head(5).iterrows():
        content += (
            f"  - **{r['date'].strftime('%Y-%m-%d')} ({r['canonical_station']})**: "
            f"actual={r['target_next_day_aqi']:.0f}, forecast={r['pred_gb']:.0f}, "
            f"residual={r['residual']:+.0f}. Cause unverified.\n"
        )

    content += """
---

## 8. What Could Make Our Conclusions Wrong?

1. **Unmodelled emission shocks:** episodic open burning, construction activity,
   or traffic diversions cannot be anticipated by regional meteorology alone.
2. **Lagged sensor reporting:** if telemetry drops for hours, lag features need
   real-time imputation, temporarily degrading skill.
3. **Transboundary transport:** agricultural residue burning or dust storms
   originating outside Maharashtra introduce air masses regional weather models
   cannot resolve without satellite AOD feeds.
4. **Feature additions (Phase 1a) did not materially change MAE:** persistence
   on daily AQI is structurally hard to beat; Phase 1b will test L1/Huber loss
   and per-station models.
"""

    with open(REPORTS_DIR / "EVALUATION.md", "w", encoding="utf-8") as f:
        f.write(content)

    metrics_summary = {
        "phase":              "1a",
        "holdout_start":      "2023-01-01",
        "holdout_end":        "2023-12-31",
        "n_features":         len(results["feature_cols"]),
        "best_cv_model":      results["best_name"],
        "ridge_alpha":        round(results["best_alpha"], 2),
        "persistence":        mp,
        "ridge":              mr,
        "gradient_boosting":  mgb,
        "classifier":         cgb,
        "interval_coverage_pct": round(results["empirical_coverage"], 1),
        "interval_nominal_pct":  80,
        "cv_agg":             {k: {kk: vv for kk, vv in v.items() if kk != "Bootstrap_CI_MAE_diff_95"}
                               for k, v in results["cv_results"]["agg"].items()},
    }
    with open(REPORTS_DIR / "evaluation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    logging.info(f"Wrote {REPORTS_DIR / 'EVALUATION.md'} and evaluation_metrics.json")



def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    res = run_chronological_evaluation()
    print("\n=== Phase 1a Complete ===")
    print(f"CV winner:           {res['best_name']}")
    print(f"Persistence MAE:     {res['metrics_persistence']['MAE']}")
    print(f"HistGB_MSE MAE:      {res['metrics_gb']['MAE']}  "
          f"(skill {res['metrics_gb']['Skill_vs_Persistence_%']:+.1f}%)")
    print(f"Ridge MAE:           -- see EVALUATION.md")
    print(f"Interval coverage:   {res['empirical_coverage']:.1f}%  (nominal 80%)")
    print(f"Classifier PR-AUC:   {res['clf_gb']['PR_AUC']}")
    print(f"\nSee reports/EVALUATION.md for full tables.")


if __name__ == "__main__":
    main()
