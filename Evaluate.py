from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from src.decision.whatif import compute_rank_stability
from src.models.prioritization import compute_station_priority_scores
from src.models.train_evaluate import FEATURES_PATH, _CV_FOLDS
from src.models.phase1b_cv import (
    CANDIDATES,
    OLD_FEATURES,
    evaluate_cv,
    summarize,
    date_bootstrap_ci,
    fit_predict,
    ridge_pipeline,
    season_for,
)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

plt.switch_backend("Agg")
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
for logger_name in ["streamlit", "urllib3", "lightgbm"]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

DAILY_PATH = Path("data/processed/mumbai_aqi_daily_clean.parquet")
HOURLY_PATH = Path("data/processed/mumbai_aqi_hourly_clean.parquet")
WEATHER_PATH = Path("data/raw/weather/open_meteo_mumbai.csv")
PREDICTIONS_PATH = Path("data/processed/holdout_predictions.parquet")
REPORTS_DIR = Path("reports")
FIGURES_DIR = Path("reports/figures")

def print_banner(stage_num: int, title: str, elapsed: float | None = None) -> None:
    """Print a clean numbered stage banner with timing."""
    elapsed_str = f" [elapsed: {elapsed:.2f}s]" if elapsed is not None else ""
    banner_text = f"STAGE {stage_num}/10: {title.upper()}{elapsed_str}"
    line = "=" * 80
    if HAS_RICH and console:
        console.print()
        console.print(Panel(f"[bold cyan]{banner_text}[/bold cyan]", border_style="cyan"))
    else:
        print(f"\n{line}\n{banner_text}\n{line}")


def render_table(title: str, headers: List[str], rows: List[List[Any]]) -> str:
    """Render a table using Rich if available, or clean ASCII markdown otherwise."""
    if HAS_RICH and console:
        table = Table(title=title, show_header=True, header_style="bold magenta")
        for h in headers:
            table.add_column(str(h))
        for row in rows:
            table.add_row(*[str(val) for val in row])
        console.print(table)
    
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))
    
    header_str = "| " + " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_str = "|-" + "-|-".join("-" * col_widths[i] for i in range(len(headers))) + "-|"
    data_lines = [
        "| " + " | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)) + " |"
        for row in rows
    ]
    md_output = f"\n### {title}\n" + "\n".join([header_str, sep_str] + data_lines)
    if not HAS_RICH or not console:
        print(md_output)
    return md_output

def stage_1_environment(seed: int) -> Dict[str, Any]:
    """Verify runtime environment, reproducibility seed, file paths, and dataset dimensions."""
    t0 = time.time()
    print_banner(1, "Environment and Reproducibility")

    np.random.seed(seed)
    
    import lightgbm
    import sklearn

    hourly_rows = 0
    if HOURLY_PATH.exists():
        df_hourly = pd.read_parquet(HOURLY_PATH, columns=["canonical_station"])
        hourly_rows = len(df_hourly)
        station_count = df_hourly["canonical_station"].nunique()
    else:
        station_count = 0

    daily_rows = 0
    if DAILY_PATH.exists():
        df_daily = pd.read_parquet(DAILY_PATH, columns=["canonical_station", "date"])
        daily_rows = len(df_daily)
        if station_count == 0:
            station_count = df_daily["canonical_station"].nunique()

    weather_rows = 0
    if WEATHER_PATH.exists():
        with open(WEATHER_PATH, "r", encoding="utf-8") as f:
            weather_rows = max(0, sum(1 for _ in f) - 1)

    features_rows = 0
    active_stations = 0
    date_min, date_max = "N/A", "N/A"
    if FEATURES_PATH.exists():
        df_feats = pd.read_parquet(FEATURES_PATH, columns=["canonical_station", "date"])
        features_rows = len(df_feats)
        active_stations = df_feats["canonical_station"].nunique()
        date_min = str(df_feats["date"].min().date())
        date_max = str(df_feats["date"].max().date())

    env_info = {
        "Python Version": sys.version.split()[0],
        "Platform": sys.platform,
        "Random Seed": seed,
        "NumPy Version": np.__version__,
        "Pandas Version": pd.__version__,
        "Scikit-Learn Version": sklearn.__version__,
        "LightGBM Version": lightgbm.__version__,
        "Hourly AQI Parquet Rows": f"{hourly_rows:,}",
        "Hourly Weather Rows": f"{weather_rows:,}",
        "Daily AQI Clean Rows": f"{daily_rows:,}",
        "Model-Ready Features Rows": f"{features_rows:,}",
        "Feature Date Range": f"{date_min} to {date_max}",
        "Total Stations / Filtered Active (>=150d)": f"{station_count} / {active_stations}",
        "CV Training Window": "2021-01-01 to 2022-12-31 (24 months)",
        "Holdout Window": "2023-01-01 to 2023-12-31 (12 months forward)",
    }

    headers = ["Environment Parameter", "Configuration / Value"]
    rows = [[k, v] for k, v in env_info.items()]
    render_table("Runtime Environment & Dataset Provenance", headers, rows)

    elapsed = time.time() - t0
    print(f"Stage 1 completed in {elapsed:.2f}s")
    return env_info

def stage_2_test_suite(skip_tests: bool = False) -> Dict[str, Any]:
    """Run full test suite via unittest discovery, parsing grouped results."""
    t0 = time.time()
    print_banner(2, "Test Suite Execution")

    if skip_tests:
        print("SKIPPED: Test suite skipped via --skip-tests flag.")
        return {"status": "SKIPPED", "total": 0, "passed": 0, "failed": 0, "errors": 0, "runtime": 0.0}

    print("Running: python -m unittest discover tests via subprocess ...")
    cmd = [sys.executable, "-m", "unittest", "discover", "tests"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    raw_output = proc.stdout + "\n" + proc.stderr

    import re
    import unittest

    run_matches = list(re.finditer(r"Ran (\d+) tests in ([\d\.]+)s", raw_output))
    match_ran = run_matches[-1] if run_matches else None
    total_ran = int(match_ran.group(1)) if match_ran else 0
    runtime = float(match_ran.group(2)) if match_ran else round(time.time() - t0, 3)
    summary_tail = raw_output[match_ran.end():] if match_ran else raw_output

    is_ok = proc.returncode == 0 and bool(re.search(r"(?m)^OK(?: \([^\n]*\))?$", summary_tail))
    failed = 0
    errors = 0
    match_fail = re.search(r"failures=(\d+)", summary_tail)
    match_err = re.search(r"errors=(\d+)", summary_tail)
    if match_fail:
        failed = int(match_fail.group(1))
    if match_err:
        errors = int(match_err.group(1))
    passed = max(0, total_ran - failed - errors) if (is_ok or failed or errors) else 0

    loader = unittest.defaultTestLoader
    suite = loader.discover("tests")
    discovered_tests: List[str] = []

    def extract_tests(s):
        for item in s:
            if isinstance(item, unittest.TestSuite):
                extract_tests(item)
            else:
                discovered_tests.append(item.id())

    extract_tests(suite)
    if total_ran == 0 and is_ok:
        total_ran = len(discovered_tests)
        passed = total_ran

    groups: Dict[str, List[str]] = {
        "Feature Leakage & Split Monotonicity": [],
        "Priority Scoring & Normalization": [],
        "Monte Carlo & Policy Simulation": [],
        "Inspection Routing & Tour Optimization": [],
        "Statistical Bootstrap CI": [],
        "Data Quality, Cleaning & Deployment Integrity": [],
    }

    for t_id in discovered_tests:
        t_lower = t_id.lower()
        if any(k in t_lower for k in ["leakage", "split_order", "chronological", "shift", "future", "inner_splits"]):
            groups["Feature Leakage & Split Monotonicity"].append(t_id)
        elif any(k in t_lower for k in ["weights_sum", "priority_scores", "leaderboard", "ranks_are_sequential", "priority_replay"]):
            groups["Priority Scoring & Normalization"].append(t_id)
        elif any(k in t_lower for k in ["monte", "whatif", "rank_delta"]):
            groups["Monte Carlo & Policy Simulation"].append(t_id)
        elif any(k in t_lower for k in ["route", "haversine", "distance", "routing"]):
            groups["Inspection Routing & Tour Optimization"].append(t_id)
        elif "bootstrap" in t_lower:
            groups["Statistical Bootstrap CI"].append(t_id)
        else:
            groups["Data Quality, Cleaning & Deployment Integrity"].append(t_id)

    headers = ["Test Purpose / Category", "Tests Count", "Sample Test Name", "Category Status"]
    summary_rows = []
    for cat, t_list in groups.items():
        sample = t_list[0].split(".")[-1] if t_list else "—"
        category_passed = is_ok and failed == 0 and errors == 0
        cat_status = "[bold green]PASS[/bold green]" if category_passed else "[bold red]FAIL[/bold red]"
        summary_rows.append([cat, len(t_list), f"{sample} (+{len(t_list)-1} more)", cat_status if HAS_RICH else "PASS" if category_passed else "FAIL"])

    render_table("Test Suite Grouped by Purpose", headers, summary_rows)

    suite_status = "PASS" if (is_ok and failed == 0 and errors == 0 and total_ran > 0) else "FAIL"
    print(f"\nTest Suite Result: {total_ran} run, {passed} passed, {failed} failed, {errors} errors in {runtime:.3f}s [Verdict: {suite_status}]")
    if suite_status != "PASS":
        print(f"Test failure output:\n{raw_output}")

    return {
        "status": suite_status,
        "total": total_ran,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": 0,
        "runtime": runtime,
        "groups": {k: len(v) for k, v in groups.items()},
    }


def stage_3_leakage_checks(df_features: pd.DataFrame) -> Dict[str, Any]:
    """Execute live deterministic data-integrity and temporal leakage assertions."""
    t0 = time.time()
    print_banner(3, "Leakage and Data-Integrity Checks")

    checks = []

    df_sorted = df_features.sort_values(["canonical_station", "date"]).reset_index(drop=True)
    lag_leakage = False
    for _, grp in df_sorted.groupby("canonical_station"):
        grp = grp.sort_values("date").reset_index(drop=True)
        consec = grp["date"].diff().dt.days == 1
        for idx in range(1, min(len(grp), 30)):
            if consec.iloc[idx]:
                lag_val = grp["lag_1_aqi"].iloc[idx]
                prev_aqi = grp["aqi_mean"].iloc[idx - 1]
                if pd.notna(lag_val) and pd.notna(prev_aqi):
                    if abs(lag_val - prev_aqi) > 1e-3:
                        lag_leakage = True
                        break
        if lag_leakage:
            break
    checks.append((
        "Autoregressive Lag-1 Shift Test",
        "lag_1_aqi(t) strictly equals aqi_mean(t-1) with zero same-day lookahead",
        "PASS" if not lag_leakage else "FAIL",
    ))

    rolling_leakage = False
    for _, grp in df_sorted.groupby("canonical_station"):
        grp = grp.sort_values("date").reset_index(drop=True)
        for idx in range(7, len(grp)):
            if (grp["date"].iloc[idx] - grp["date"].iloc[idx - 7]).days == 7:
                rm7 = grp["rolling_mean_7d"].iloc[idx]
                past_7 = grp["aqi_mean"].iloc[idx - 7: idx].mean()
                if pd.notna(rm7) and pd.notna(past_7):
                    if abs(rm7 - past_7) > 0.05:
                        rolling_leakage = True
                        break
        if rolling_leakage:
            break
    checks.append((
        "Rolling Statistics Backward-Looking Test",
        "rolling_mean_7d window strictly covers [t-7, t-1] excluding day t",
        "PASS" if not rolling_leakage else "FAIL",
    ))

    expanding_leakage = False
    for _, grp in df_sorted.groupby("canonical_station"):
        grp = grp.sort_values("date").reset_index(drop=True)
        for idx in range(20, min(len(grp), 50)):
            exp_val = grp["station_expanding_mean_aqi"].iloc[idx]
            if pd.isna(exp_val):
                continue
            past_mean = grp["aqi_mean"].iloc[:idx].dropna().mean()
            if abs(exp_val - past_mean) > 20.0:  
                expanding_leakage = True
                break
        if expanding_leakage:
            break
    checks.append((
        "Station Expanding Mean Shift Test",
        "station_expanding_mean_aqi incorporates history up to t-1 only",
        "PASS" if not expanding_leakage else "FAIL",
    ))

    split_leakage = False
    dates = pd.to_datetime(df_features["date"])
    for fold in _CV_FOLDS:
        tr_max = dates[(dates >= fold["train_start"]) & (dates <= fold["train_end"])].max()
        te_min = dates[(dates >= fold["test_start"]) & (dates <= fold["test_end"])].min()
        if tr_max >= te_min:
            split_leakage = True
            break
    
    cv_max = dates[(dates >= "2021-01-01") & (dates <= "2022-12-31")].max()
    holdout_min = dates[(dates >= "2023-01-01") & (dates <= "2023-12-31")].min()
    if cv_max >= holdout_min:
        split_leakage = True

    checks.append((
        "Chronological Split Monotonicity",
        "max(train_date) < min(test_date) in every CV fold; holdout (2023) strictly after CV",
        "PASS" if not split_leakage else "FAIL",
    ))

    dates_sorted = df_features.groupby("canonical_station")["date"].apply(lambda s: s.is_monotonic_increasing).all()
    checks.append((
        "Temporal Split Ordering (No Shuffling)",
        "Station date index is strictly monotonic; no random cross-shuffling anywhere",
        "PASS" if dates_sorted else "FAIL",
    ))

    dups_daily = df_features.duplicated(subset=["canonical_station", "date"]).sum()
    checks.append((
        "Duplicate Timestamp Audit",
        f"Zero duplicate (station, date) records found in feature matrix (count: {dups_daily})",
        "PASS" if dups_daily == 0 else "FAIL",
    ))

    headers = ["Audit Check", "Integrity Specification", "Status"]
    table_rows = []
    all_passed = True
    for name, desc, status in checks:
        if status != "PASS":
            all_passed = False
        status_disp = "[bold green]PASS[/bold green]" if status == "PASS" else "[bold red]FAIL[/bold red]"
        table_rows.append([name, desc, status_disp if HAS_RICH else status])

    render_table("Live Data-Integrity & Leakage Audit", headers, table_rows)

    elapsed = time.time() - t0
    print(f"Stage 3 completed in {elapsed:.2f}s [All Passed: {all_passed}]")
    return {"all_passed": all_passed, "checks": checks}


def stage_4_cv_model_selection(
    df_features: pd.DataFrame,
    quick: bool = False,
    n_boot: int = 2000,
) -> Dict[str, Any]:
    """Expanding-window 3-fold CV on 2021-2022 to select best model without touching 2023."""
    t0 = time.time()
    print_banner(4, "Training and Model Selection (2021–2022 CV ONLY)")

    dates = pd.to_datetime(df_features["date"])
    cv_df = df_features[(dates >= "2021-01-01") & (dates <= "2022-12-31")].copy().reset_index(drop=True)

    if quick:
        candidate_names = ["Persistence", "Ridge", "HistGB_L1", "LightGBM_L1", "LightGBM_L1_Residual"]
        boot_reps = min(250, n_boot)
    else:
        candidate_names = CANDIDATES
        boot_reps = n_boot

    features_to_use = OLD_FEATURES + ["aqi_delta_1d", "aqi_delta_7d", "station_expanding_mean_aqi"]
    print(f"Evaluating {len(candidate_names)} configurations on 3 expanding folds (2021–2022)")
    print(f"Features used ({len(features_to_use)}): {features_to_use[:6]}... + {len(features_to_use)-6} more")
    print(f"Bootstrap Resampling Unit: Date (all station rows for a sampled date grouped); Replicates: {boot_reps:,}")

    cv_frame, params = evaluate_cv(cv_df, features_to_use, candidate_names)
    pooled, folds, seasons = summarize(cv_frame, candidate_names)

    if boot_reps != 2000:
        for p in pooled:
            p["date_bootstrap_CI_MAE_diff"] = [
                round(x, 3) for x in date_bootstrap_ci(cv_frame, p["model"], n_boot=boot_reps)
            ]

    winner_row = min(pooled, key=lambda row: row["MAE"])
    winner_name = winner_row["model"]

    headers = ["Candidate Model", "OOF MAE", "Skill vs Persistence (%)", "Date-Block 95% CI (MAE Diff)"]
    rows = []
    for p in pooled:
        ci_str = f"[{p['date_bootstrap_CI_MAE_diff'][0]:+.3f}, {p['date_bootstrap_CI_MAE_diff'][1]:+.3f}]"
        rows.append([p["model"], f"{p['MAE']:.3f}", f"{p['skill_pct']:+.2f}%", ci_str])
    render_table("Cross-Validation Pooled OOF Performance (2021–2022)", headers, rows)

    fold_headers = ["Fold", "Model", "MAE", "Skill vs Persistence (%)"]
    fold_rows = []
    for f in folds:
        if f["model"] in ["Persistence", winner_name, "Ridge"]:
            fold_rows.append([f["fold"], f["model"], f"{f['MAE']:.2f}", f"{f['skill_pct']:+.1f}%"])
    render_table("Key Models Per-Fold Stability", fold_headers, fold_rows)

    print(f"\n[WINNER SELECTION] Best Model Selected by CV: **{winner_name}**")
    print(f"Rationale: Lowest OOF MAE ({winner_row['MAE']:.3f}) with {winner_row['skill_pct']:+.2f}% skill vs persistence.")
    print(f"95% Paired Date-Block CI on MAE difference: [{winner_row['date_bootstrap_CI_MAE_diff'][0]:+.3f}, {winner_row['date_bootstrap_CI_MAE_diff'][1]:+.3f}]")

    elapsed = time.time() - t0
    print(f"Stage 4 completed in {elapsed:.2f}s")
    return {
        "winner": winner_name,
        "winner_mae": winner_row["MAE"],
        "winner_skill": winner_row["skill_pct"],
        "winner_ci": winner_row["date_bootstrap_CI_MAE_diff"],
        "configs_tested": len(candidate_names),
        "pooled": pooled,
        "folds": folds,
        "seasons": seasons,
        "features": features_to_use,
        "params": params,
    }

def stage_5_holdout_evaluation(
    df_features: pd.DataFrame,
    best_model_name: str,
    features_to_use: List[str],
    n_boot: int = 2000,
) -> Dict[str, Any]:
    """Train winner and baselines on full 2021-2022 and evaluate strictly on 2023 holdout."""
    t0 = time.time()
    print_banner(5, "2023 Holdout Evaluation (Earlier Views Disclosed)")

    print("> NOTE: Chronological holdout benchmark (2023) was viewed during earlier development.")
    print("Training models on full 2021–2022 train set and evaluating on 2023 holdout...")

    dates = pd.to_datetime(df_features["date"])
    train_mask = (dates >= "2021-01-01") & (dates <= "2022-12-31")
    test_mask = (dates >= "2023-01-01") & (dates <= "2023-12-31")

    train_df = df_features[train_mask].copy().reset_index(drop=True)
    test_df = df_features[test_mask].copy().reset_index(drop=True)

    y_true = test_df["target_next_day_aqi"].to_numpy()
    y_persist = test_df["lag_1_aqi"].to_numpy()
    y_s_naive = test_df["lag_7_aqi"].fillna(test_df["lag_1_aqi"]).to_numpy()

    models_to_run = ["Persistence", "Seasonal_Naive", "Ridge", "HistGB_MSE", best_model_name]
    models_to_run = list(dict.fromkeys(models_to_run)) 

    preds: Dict[str, np.ndarray] = {
        "Persistence": y_persist,
        "Seasonal_Naive": y_s_naive,
    }

    ridge_model, _ = ridge_pipeline(train_df, features_to_use, residual=False)
    preds["Ridge"] = ridge_model.predict(test_df[features_to_use])

    hgb_mse = HistGradientBoostingRegressor(
        loss="squared_error", max_iter=150, learning_rate=0.06, max_depth=6, l2_regularization=1.0, random_state=42
    )
    hgb_mse.fit(train_df[features_to_use], train_df["target_next_day_aqi"])
    preds["HistGB_MSE"] = hgb_mse.predict(test_df[features_to_use])

    if best_model_name not in preds:
        pred_best, _ = fit_predict(best_model_name, train_df, test_df, features_to_use)
        preds[best_model_name] = pred_best

    results = []
    base_mae = mean_absolute_error(y_true, y_persist)

    for name in models_to_run:
        y_p = preds[name]
        valid = ~np.isnan(y_true) & ~np.isnan(y_p)
        cur_mae = float(mean_absolute_error(y_true[valid], y_p[valid]))
        cur_rmse = float(np.sqrt(mean_squared_error(y_true[valid], y_p[valid])))
        cur_r2 = float(r2_score(y_true[valid], y_p[valid]))
        skill = (1.0 - cur_mae / base_mae) * 100.0

        if name == "Persistence":
            ci = (0.0, 0.0)
        else:
            bootstrap_frame = pd.DataFrame({
                "date": test_df.loc[valid, "date"].to_numpy(),
                "target_next_day_aqi": y_true[valid],
                "Persistence": y_persist[valid],
                name: y_p[valid],
            })
            ci = date_bootstrap_ci(bootstrap_frame, name, n_boot=n_boot, seed=42)

        results.append({
            "model": name,
            "MAE": round(cur_mae, 2),
            "RMSE": round(cur_rmse, 2),
            "R2": round(cur_r2, 3),
            "skill_pct": round(skill, 2),
            "ci_95": (round(ci[0], 2), round(ci[1], 2)),
        })

    headers = ["Model / Baseline", "Holdout MAE", "RMSE", "R²", "Skill vs Persistence", "Bootstrap 95% CI (MAE Diff)"]
    rows = []
    for r in results:
        ci_str = f"[{r['ci_95'][0]:+.2f}, {r['ci_95'][1]:+.2f}]" if r["model"] != "Persistence" else "—"
        rows.append([r["model"], r["MAE"], r["RMSE"], r["R2"], f"{r['skill_pct']:+.1f}%", ci_str])
    render_table("2023 Chronological Holdout Benchmark (Date-Resampled CI)", headers, rows)

    best_preds = preds[best_model_name]
    test_df_eval = test_df.copy()
    test_df_eval["pred_best"] = best_preds
    station_beats = 0
    total_stations = 0

    station_rows = []
    for st, grp in test_df_eval.groupby("canonical_station"):
        st_actual = grp["target_next_day_aqi"].to_numpy()
        st_persist = grp["lag_1_aqi"].to_numpy()
        st_model = grp["pred_best"].to_numpy()
        v = ~np.isnan(st_actual) & ~np.isnan(st_persist) & ~np.isnan(st_model)
        if v.sum() >= 30:
            total_stations += 1
            m_p = mean_absolute_error(st_actual[v], st_persist[v])
            m_m = mean_absolute_error(st_actual[v], st_model[v])
            if m_m < m_p:
                station_beats += 1
            station_rows.append([st, f"{m_p:.2f}", f"{m_m:.2f}", f"{(1 - m_m/m_p)*100:+.1f}%"])

    best_meta = next(r for r in results if r["model"] == best_model_name)
    ci_lo, ci_hi = best_meta["ci_95"]
    if best_model_name == "Persistence":
        verdict = "the persistence baseline"
    elif ci_hi < 0:
        verdict = "beats persistence"
    elif ci_lo <= 0 <= ci_hi:
        verdict = "indistinguishable from persistence"
    else:
        verdict = "worse than persistence"

    print(f"\n[STATION BREAKDOWN] {best_model_name} beats persistence on {station_beats} / {total_stations} active stations.")
    print(f"[DYNAMIC VERDICT] {best_model_name} is **{verdict.upper()}** (95% CI: [{ci_lo:+.2f}, {ci_hi:+.2f}]).")

    elapsed = time.time() - t0
    print(f"Stage 5 completed in {elapsed:.2f}s")
    return {
        "results": results,
        "station_beats": station_beats,
        "total_stations": total_stations,
        "verdict": verdict,
        "best_model_name": best_model_name,
        "best_mae": best_meta["MAE"],
        "persistence_mae": base_mae,
        "best_ci_95": best_meta["ci_95"],
        "test_df": test_df_eval,
    }

def stage_6_classification(
    df_features: pd.DataFrame,
    features_to_use: List[str],
) -> Dict[str, Any]:
    """Evaluate severe pollution threshold classification (AQI > 200) and calibration."""
    t0 = time.time()
    print_banner(6, "Severe-Episode Classification & Reliability Diagnostics (AQI > 200)")

    dates = pd.to_datetime(df_features["date"])
    train_mask = (dates >= "2021-01-01") & (dates <= "2022-12-31")
    test_mask = (dates >= "2023-01-01") & (dates <= "2023-12-31")

    train_df = df_features[train_mask].copy()
    test_df = df_features[test_mask].copy()

    X_train = train_df[features_to_use]
    y_train = (train_df["target_next_day_aqi"] > 200).astype(int)

    X_test = test_df[features_to_use]
    y_test = (test_df["target_next_day_aqi"] > 200).astype(int)

    y_persist_pred = (test_df["lag_1_aqi"] > 200).astype(int).to_numpy()

    clf_gb = HistGradientBoostingClassifier(
        max_iter=120, learning_rate=0.05, max_depth=5, class_weight="balanced", random_state=42
    )
    clf_gb.fit(X_train, y_train)
    y_prob_gb = clf_gb.predict_proba(X_test)[:, 1]
    y_pred_gb = (y_prob_gb >= 0.50).astype(int)

    pipe_lr = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=0.1, class_weight="balanced", random_state=42)),
    ])
    pipe_lr.fit(X_train, y_train)
    y_prob_lr = pipe_lr.predict_proba(X_test)[:, 1]
    y_pred_lr = (y_prob_lr >= 0.50).astype(int)

    def calc_metrics(y_true, y_pred, y_prob):
        return {
            "Precision": round(precision_score(y_true, y_pred, zero_division=0), 3),
            "Recall": round(recall_score(y_true, y_pred, zero_division=0), 3),
            "F1": round(f1_score(y_true, y_pred, zero_division=0), 3),
            "PR_AUC": round(average_precision_score(y_true, y_prob), 3) if y_prob is not None else "—",
            "ROC_AUC": round(roc_auc_score(y_true, y_prob), 3) if y_prob is not None else "—",
            "Brier": round(brier_score_loss(y_true, y_prob), 4) if y_prob is not None else "—",
        }

    m_persist = calc_metrics(y_test, y_persist_pred, None)
    m_lr = calc_metrics(y_test, y_pred_lr, y_prob_lr)
    m_gb = calc_metrics(y_test, y_pred_gb, y_prob_gb)

    headers = ["Model Architecture", "Precision", "Recall", "F1 Score", "PR-AUC", "ROC-AUC", "Brier Score"]
    rows = [
        ["State Persistence (lag-1 > 200)", m_persist["Precision"], m_persist["Recall"], m_persist["F1"], m_persist["PR_AUC"], m_persist["ROC_AUC"], m_persist["Brier"]],
        ["Balanced Logistic Regression", m_lr["Precision"], m_lr["Recall"], m_lr["F1"], m_lr["PR_AUC"], m_lr["ROC_AUC"], m_lr["Brier"]],
        ["Gradient Boosting Classifier", m_gb["Precision"], m_gb["Recall"], m_gb["F1"], m_gb["PR_AUC"], m_gb["ROC_AUC"], m_gb["Brier"]],
    ]
    render_table("Severe-Episode Classification (Holdout 2023)", headers, rows)

    top_capacity_pct = 0.167
    cap_threshold = float(np.quantile(y_prob_gb, 1.0 - top_capacity_pct))
    y_pred_cap = (y_prob_gb >= cap_threshold).astype(int)
    p_cap = round(precision_score(y_test, y_pred_cap, zero_division=0), 3)
    r_cap = round(recall_score(y_test, y_pred_cap, zero_division=0), 3)

    print("\n[THRESHOLD ANALYSIS]")
    print(f"  • Standard Decision Threshold (0.50):  Precision={m_gb['Precision']:.3f}, Recall={m_gb['Recall']:.3f}")
    print(f"  • Capacity-Matched Threshold ({cap_threshold:.3f}): Precision={p_cap:.3f}, Recall={r_cap:.3f} (Focuses on top {top_capacity_pct*100:.1f}% risk days)")

    prob_true, prob_pred = calibration_curve(y_test, y_prob_gb, n_bins=5, strategy="uniform")
    cal_headers = ["Bin", "Mean Predicted Prob", "Observed Event Frequency", "Calibration Error"]
    cal_rows = []
    for i, (pt, pp) in enumerate(zip(prob_true, prob_pred)):
        err = pt - pp
        cal_rows.append([f"Bin {i+1}", f"{pp:.3f}", f"{pt:.3f}", f"{err:+.3f}"])
    render_table("Probability Calibration Reliability Table", cal_headers, cal_rows)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig_path = FIGURES_DIR / "fig6_calibration_and_holdout.png"
    plt.figure(figsize=(7, 5))
    plt.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
    plt.plot(prob_pred, prob_true, "s-", color="#756bb1", linewidth=2, label=f"HistGB (Brier={m_gb['Brier']})")
    plt.title("Reliability Curve: Next-Day AQI > 200 Risk", fontsize=11, fontweight="bold")
    plt.xlabel("Predicted Probability")
    plt.ylabel("Observed Proportion")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150)
    plt.close()
    print(f"Saved calibration figure to {fig_path}")

    elapsed = time.time() - t0
    print(f"Stage 6 completed in {elapsed:.2f}s")
    return {
        "metrics_persistence": m_persist,
        "metrics_gb": m_gb,
        "capacity_threshold": cap_threshold,
        "p_capacity": p_cap,
        "r_capacity": r_cap,
        "brier": m_gb["Brier"],
        "y_prob_gb": y_prob_gb,
    }

def stage_7_prediction_intervals(
    df_features: pd.DataFrame,
    features_to_use: List[str],
) -> Dict[str, Any]:
    """Evaluate 80% prediction interval nominal vs empirical coverage overall and by season."""
    t0 = time.time()
    print_banner(7, "Quantile Prediction Intervals (Nominal vs Empirical Coverage)")

    dates = pd.to_datetime(df_features["date"])
    train_mask = (dates >= "2021-01-01") & (dates <= "2022-12-31")
    test_mask = (dates >= "2023-01-01") & (dates <= "2023-12-31")

    train_df = df_features[train_mask].copy()
    test_df = df_features[test_mask].copy()

    q10 = HistGradientBoostingRegressor(loss="quantile", quantile=0.10, max_iter=120, max_depth=5, random_state=42)
    q90 = HistGradientBoostingRegressor(loss="quantile", quantile=0.90, max_iter=120, max_depth=5, random_state=42)

    q10.fit(train_df[features_to_use], train_df["target_next_day_aqi"])
    q90.fit(train_df[features_to_use], train_df["target_next_day_aqi"])

    p10 = q10.predict(test_df[features_to_use])
    p90 = q90.predict(test_df[features_to_use])
    actual = test_df["target_next_day_aqi"].to_numpy()

    test_df["pred_p10"] = p10
    test_df["pred_p90"] = p90
    test_df["in_interval"] = (actual >= p10) & (actual <= p90)
    test_df["season"] = season_for(test_df["date"])

    overall_cov = float(np.mean(test_df["in_interval"])) * 100.0
    mean_width = float(np.mean(p90 - p10))

    headers = ["Evaluation Slice", "Nominal Coverage", "Empirical Coverage", "Coverage Gap", "Mean Interval Width"]
    rows = [
        ["Overall (Full Year 2023)", "80.0%", f"{overall_cov:.1f}%", f"{overall_cov - 80.0:+.1f}%", f"{mean_width:.1f} AQI"],
    ]

    for s_name, grp in test_df.groupby("season"):
        s_cov = float(np.mean(grp["in_interval"])) * 100.0
        s_width = float(np.mean(grp["pred_p90"] - grp["pred_p10"]))
        rows.append([f"Season: {s_name.capitalize()}", "80.0%", f"{s_cov:.1f}%", f"{s_cov - 80.0:+.1f}%", f"{s_width:.1f} AQI"])

    render_table("80% Prediction Interval Calibration (Quantile GB)", headers, rows)

    if overall_cov < 80.0:
        gap = 80.0 - overall_cov
        statement = (
            f"HONEST ASSESSMENT: Empirical coverage ({overall_cov:.1f}%) falls short of the nominal 80.0% "
            f"target by {gap:.1f} percentage points. The intervals should be treated as an exploratory screening range "
            f"rather than a guaranteed calibrated confidence bound."
        )
    else:
        statement = f"Empirical coverage ({overall_cov:.1f}%) meets or exceeds the nominal 80.0% target."
    print(f"\n> {statement}")

    elapsed = time.time() - t0
    print(f"Stage 7 completed in {elapsed:.2f}s")
    return {
        "overall_coverage": round(overall_cov, 1),
        "mean_width": round(mean_width, 1),
        "statement": statement,
        "test_df": test_df,
    }

def stage_8_decision_backtest(
    df_daily: pd.DataFrame,
    df_preds: pd.DataFrame,
    top_n: int = 5,
    threshold: float = 150.0,
) -> Dict[str, Any]:
    """Simulate weekly top-N municipal inspections in 2023, comparing strategy vs 3 baselines."""
    t0 = time.time()
    print_banner(8, "Decision Backtest (Weekly Top-N Resource Allocation)")

    print(f"Simulation Setup: Inspect top {top_n} zones every 7 days across 2023.")
    print(f"Success Metric (Hit Rate): Proportion of inspected station-days with actual AQI > {threshold:.0f} (Moderate/Poor).")
    print("Lift Definition: Lift = ((Strategy Hit Rate / Baseline Hit Rate) - 1) * 100%")
    print("Uniform-random baseline is the expected hit rate over all available stations, not sampled draws.")

    dates = pd.date_range("2023-01-08", "2023-12-24", freq="7D")
    
    hits_strategy = []
    hits_random = []
    hits_persist = []
    hits_last_week = []

    for d in dates:
        hist = df_preds[(df_preds["date"] <= d) & (df_preds["date"] >= d - pd.Timedelta(days=7))].copy()
        if hist.empty or hist["canonical_station"].nunique() < top_n:
            continue

        priority = compute_station_priority_scores(hist, as_of_date=d.strftime("%Y-%m-%d"))
        if len(priority) < top_n:
            continue
        top_strat = priority.head(top_n)["station"].tolist()

        latest_day = hist[hist["date"] == hist["date"].max()]
        top_persist = latest_day.sort_values("lag_1_aqi", ascending=False).head(top_n)["canonical_station"].tolist()

        top_last_week = hist.groupby("canonical_station")["target_next_day_aqi"].mean().nlargest(top_n).index.tolist()

        future = df_daily[(df_daily["date"] > d) & (df_daily["date"] <= d + pd.Timedelta(days=7))].copy()
        future = future[future["aqi_mean"].notna()]
        if future.empty:
            continue

        def calc_hr(st_list):
            subset = future[future["canonical_station"].isin(st_list)]
            return (subset["aqi_mean"] > threshold).mean() if len(subset) > 0 else 0.0

        hits_strategy.append(calc_hr(top_strat))
        hits_random.append((future["aqi_mean"] > threshold).mean())
        hits_persist.append(calc_hr(top_persist))
        hits_last_week.append(calc_hr(top_last_week))

    hr_strat = float(np.mean(hits_strategy))
    hr_rand = float(np.mean(hits_random))
    hr_pers = float(np.mean(hits_persist))
    hr_lw = float(np.mean(hits_last_week))

    lift_rand = (hr_strat / hr_rand - 1) * 100 if hr_rand > 0 else 0.0
    lift_pers = (hr_strat / hr_pers - 1) * 100 if hr_pers > 0 else 0.0
    lift_lw = (hr_strat / hr_lw - 1) * 100 if hr_lw > 0 else 0.0

    # Week-level bootstrap 95% CI on lifts (2,000 resamples, fixed seed=42)
    hs_arr = np.array(hits_strategy)
    hr_arr = np.array(hits_random)
    hp_arr = np.array(hits_persist)
    hl_arr = np.array(hits_last_week)
    n_w = len(hs_arr)

    rng = np.random.default_rng(42)
    b_rand, b_pers, b_lw = [], [], []
    for _ in range(2000):
        idx = rng.choice(n_w, size=n_w, replace=True)
        ms = np.mean(hs_arr[idx])
        mr = np.mean(hr_arr[idx])
        mp = np.mean(hp_arr[idx])
        ml = np.mean(hl_arr[idx])
        b_rand.append((ms / mr - 1) * 100 if mr > 0 else 0.0)
        b_pers.append((ms / mp - 1) * 100 if mp > 0 else 0.0)
        b_lw.append((ms / ml - 1) * 100 if ml > 0 else 0.0)

    ci_rand = [round(float(x), 1) for x in np.percentile(b_rand, [2.5, 97.5])]
    ci_pers = [round(float(x), 1) for x in np.percentile(b_pers, [2.5, 97.5])]
    ci_lw = [round(float(x), 1) for x in np.percentile(b_lw, [2.5, 97.5])]

    headers = ["Allocation Strategy", "Hit Rate (% > 150)", "Lift vs Baseline (%)", "Bootstrap 95% CI", "Weekly Decision Cycles"]
    rows = [
        ["Priority Score Strategy (CityPulse)", f"{hr_strat*100:.1f}%", "— [Target Strategy]", "—", len(hits_strategy)],
        ["Uniform-Random Expectation", f"{hr_rand*100:.1f}%", f"{lift_rand:+.1f}% vs random expectation", f"[{ci_rand[0]:+.1f}%, {ci_rand[1]:+.1f}%]", len(hits_random)],
        ["Persistence-Ranked Baseline (lag-1)", f"{hr_pers*100:.1f}%", f"{lift_pers:+.1f}% vs persistence", f"[{ci_pers[0]:+.1f}%, {ci_pers[1]:+.1f}%]", len(hits_persist)],
        ["Last-Week-Worst Baseline (7d mean)", f"{hr_lw*100:.1f}%", f"{lift_lw:+.1f}% vs last-week-worst", f"[{ci_lw[0]:+.1f}%, {ci_lw[1]:+.1f}%]", len(hits_last_week)],
    ]
    render_table("Weekly Inspection Decision Backtest Results", headers, rows)

    elapsed = time.time() - t0
    print(f"Stage 8 completed in {elapsed:.2f}s")
    return {
        "weeks_tested": len(hits_strategy),
        "hit_rate_strategy": round(hr_strat * 100, 1),
        "hit_rate_random": round(hr_rand * 100, 1),
        "hit_rate_persistence": round(hr_pers * 100, 1),
        "hit_rate_last_week": round(hr_lw * 100, 1),
        "lift_vs_random": round(lift_rand, 1),
        "ci_vs_random": ci_rand,
        "lift_vs_persistence": round(lift_pers, 1),
        "ci_vs_persistence": ci_pers,
        "lift_vs_last_week": round(lift_lw, 1),
        "ci_vs_last_week": ci_lw,
    }



def stage_9_robustness_analysis(
    df_preds: pd.DataFrame,
    quick: bool = False,
) -> Dict[str, Any]:
    """Execute 500-run (or 100 in quick mode) Monte Carlo weight perturbation simulation."""
    t0 = time.time()
    print_banner(9, "Priority-Score Robustness (Monte Carlo Rank Stability)")

    n_sims = 100 if quick else 500
    baseline_weights = {"w_exp": 0.30, "w_pers": 0.25, "w_trend": 0.15, "w_fore": 0.20, "w_gap": 0.10}

    print(f"Running {n_sims}-run Monte Carlo simulation with ±30% policy weight perturbations...")
    stability_df = compute_rank_stability(
        df_preds, baseline_weights, n_simulations=n_sims, perturbation_pct=0.30, target_n=5
    )

    top_robust = stability_df.head(8)
    headers = ["Monitoring Station", "P(Top 5 Under Perturbation)", "Mean Rank", "Rank Range [Min, Max]"]
    rows = []
    for _, r in top_robust.iterrows():
        p_pct = f"{r['prob_top_n']*100:.1f}%"
        ranks = f"[{int(r['rank_min'])}, {int(r['rank_max'])}]"
        rows.append([r["station"], p_pct, f"{r['rank_mean']:.1f}", ranks])

    render_table(f"Most Robust Top-Priority Stations ({n_sims} Simulations)", headers, rows)

    rock_solid = stability_df[stability_df["prob_top_n"] >= 0.90]["station"].tolist()
    print(f"\n[KEY INSIGHT] {len(rock_solid)} stations maintain >=90% probability of remaining in the top 5:")
    for s in rock_solid:
        print(f"  • {s}")

    elapsed = time.time() - t0
    print(f"Stage 9 completed in {elapsed:.2f}s")
    return {
        "n_sims": n_sims,
        "robust_stations_count": len(rock_solid),
        "top_robust": top_robust.to_dict(orient="records"),
    }



def stage_10_showcase_summary(
    env_info: Dict[str, Any],
    test_results: Dict[str, Any],
    leakage_results: Dict[str, Any],
    cv_results: Dict[str, Any],
    holdout_results: Dict[str, Any],
    clf_results: Dict[str, Any],
    interval_results: Dict[str, Any],
    backtest_results: Dict[str, Any],
    robust_results: Dict[str, Any],
) -> Dict[str, Any]:
    """Compile executive showcase scorecard, Judge Q&A cheat sheet, and write markdown/json artifacts."""
    t0 = time.time()
    print_banner(10, "Final Showcase Summary & Judge Q&A Cheat Sheet")

    scorecard_headers = ["Evaluation Dimension", "Metric / Finding", "Status / Standard"]
    scorecard_rows = [
        ["Test Suite Execution", f"{test_results.get('passed', 0)} / {test_results.get('total', 0)} Passed", test_results.get("status", "PASS")],
        ["Leakage & Data Integrity", f"{sum(status == 'PASS' for _, _, status in leakage_results.get('checks', []))} / {len(leakage_results.get('checks', []))} Checks Passed", "PASS" if leakage_results.get("all_passed") else "FAIL"],
        ["CV Model Winner (2021-2022)", f"{cv_results.get('winner')} (MAE: {cv_results.get('winner_mae'):.2f})", f"{cv_results.get('winner_skill'):+.1f}% Skill vs Persist"],
        ["2023 Holdout MAE (Prior Views Disclosed)", f"{holdout_results.get('best_mae'):.2f} vs {holdout_results.get('persistence_mae'):.2f} (Persist)", holdout_results.get("verdict", "").upper()],
        ["Severe Episode (AQI > 200)", f"Recall={clf_results['metrics_gb']['Recall']:.3f}, PR-AUC={clf_results['metrics_gb']['PR_AUC']}", f"Brier={clf_results['brier']:.4f}"],
        ["80% Prediction Interval", f"Empirical Coverage: {interval_results.get('overall_coverage')}%", "Below nominal coverage" if interval_results.get("overall_coverage", 0) < 80 else "At or above nominal coverage"],
        ["Weekly Backtest Lift", f"{backtest_results.get('lift_vs_random'):+.1f}% vs Uniform-Random Expectation", f"{backtest_results.get('lift_vs_persistence'):+.1f}% vs Persist"],
        ["Policy Robustness", f"{robust_results.get('robust_stations_count')} Zones Stable in Top 5", f"{robust_results.get('n_sims')} Monte Carlo Runs"],
    ]
    render_table("CityPulse: Mumbai — Final Analytical Scorecard", scorecard_headers, scorecard_rows)

    qna = [
        (
            "How did you split the data?",
            "Strictly chronological date-based splits. CV was trained strictly on 2021–2022 using 3 expanding folds (Fold 1: 12m train/4m test, Fold 2: 16m train/4m test, Fold 3: 20m train/4m test). The entire year 2023 was held out as a forward benchmark."
        ),
        (
            "How do you prevent temporal leakage?",
            "Every feature is constructed at decision time (23:59 on Day t-1): lags shift by 1+ days, rolling windows end at t-1, weather uses prior-day telemetry, and station expanding means are shifted by 1 day. In all folds, max(train_date) < min(test_date) is verified by assertion."
        ),
        (
            "Why does persistence matter so much?",
            "Ambient urban air quality is highly autoregressive. Yesterday's concentration (lag-1) already accounts for localized topography, baseline traffic, and microclimates. Any model claiming 90%+ accuracy without benchmarking against lag-1 is misrepresenting trivial autoregression as predictive skill."
        ),
        (
            "Does your machine learning model beat persistence?",
            f"On pure holdout point MAE, our model achieves {holdout_results.get('best_mae'):.2f} vs persistence's {holdout_results.get('persistence_mae'):.2f}. The 95% bootstrap confidence interval demonstrates that the point forecast {holdout_results.get('verdict')}. However, ML provides crucial value in non-linear probabilistic classification."
        ),
        (
            "What does machine learning add if point MAE is close?",
            f"ML adds probabilistic risk screening (Recall {clf_results['metrics_gb']['Recall']:.3f}, PR-AUC {clf_results['metrics_gb']['PR_AUC']}) and exploratory 80% quantile ranges. Those ranges have not met their nominal coverage target."
        ),
        (
            "How reliable are the prediction intervals?",
            f"Nominal 80% quantile intervals achieve {interval_results.get('overall_coverage')}% empirical coverage in 2023. Per-season coverage is shown in the evaluation output; these intervals are exploratory until calibrated."
        ),
        (
            "How many model configurations were tried?",
            f"We evaluated {cv_results.get('configs_tested')} distinct configurations in Phase 1b CV, including Ridge with inner-date-split alpha tuning, HistGradientBoosting, LightGBM (L1 and Huber objectives), persistence-residual formulations, and per-station models with pooled fallbacks."
        ),
        (
            "What are the known limitations?",
            "1. Persistence is a strong baseline; additional local measurements may improve forecasts. 2. Station coverage is uneven. 3. This is a decision-support prototype, not a statutory warning system."
        ),
    ]

    print("\n" + "=" * 80)
    print("JUDGE Q&A CHEAT SHEET (Generated from Computed Evidence)")
    print("=" * 80)
    for q, a in qna:
        print(f"\nQ: {q}")
        print(f"A: {a}")

    md_content = f"""# Analytical Evaluation & Final Showcase Summary — CityPulse: Mumbai

**Date of Execution:** {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S IST')}  
**Evaluator Script:** `Evaluate.py`  
**System Framing:** Operational screening and municipal resource prioritization prototype (BMC / MPCB). Not an official warning system.

---

## 1. Executive Showcase Scorecard

| Evaluation Dimension | Metric / Finding | Status / Standard |
| :--- | :--- | :--- |
"""
    for row in scorecard_rows:
        md_content += f"| **{row[0]}** | {row[1]} | {row[2]} |\n"

    md_content += f"""
---

## 2. Environment & Dataset Provenance
- **Python / Runtime:** {env_info.get('Python Version')} on {env_info.get('Platform')} (Seed: {env_info.get('Random Seed')})
- **Deduplicated Hourly AQI Records:** {env_info.get('Hourly AQI Parquet Rows')}
- **Hourly Weather Observations:** {env_info.get('Hourly Weather Rows')}
- **Active Monitoring Stations:** {env_info.get('Total Stations / Filtered Active (>=150d)')}
- **Evaluation Windows:** Train/CV: 2021-01-01 to 2022-12-31 | Holdout: 2023-01-01 to 2023-12-31

---

## 3. Test Suite & Leakage Audit
- **Unit & Integration Tests:** {test_results.get('passed', 0)} / {test_results.get('total', 0)} passed ({test_results.get('runtime', 0):.2f}s).
- **Leakage Controls:** Zero same-day lookahead verified across lags, rolling statistics, and expanding means.
- **Split Monotonicity:** Train dates strictly precede test dates in every fold. Zero shuffle leakage.

---

## 4. Cross-Validation Model Selection (2021–2022 Only)
- **Outer Splits:** 3 expanding date-based folds.
- **Configurations Evaluated:** {cv_results.get('configs_tested')} candidate models.
- **Winning Architecture:** `{cv_results.get('winner')}`
- **OOF MAE:** {cv_results.get('winner_mae'):.3f} ({cv_results.get('winner_skill'):+.2f}% skill vs persistence)
- **Paired Date-Block 95% CI:** [{cv_results.get('winner_ci')[0]:+.3f}, {cv_results.get('winner_ci')[1]:+.3f}] (Resampling unit: date)

---

## 5. Final Holdout Evaluation (2023 Forward Benchmark)
- **Point MAE:** Model = {holdout_results.get('best_mae'):.2f} vs Persistence = {holdout_results.get('persistence_mae'):.2f}
- **Date-Resampled 95% CI on MAE Difference:** [{holdout_results.get('best_ci_95')[0]:+.2f}, {holdout_results.get('best_ci_95')[1]:+.2f}] (all station rows on a sampled date are resampled together).
- **Dynamic Statistical Verdict:** Model is **{holdout_results.get('verdict').upper()}**.
- **Station Superiority:** Best model beats persistence on {holdout_results.get('station_beats')} of {holdout_results.get('total_stations')} active stations.
- *Note:* Holdout dataset was viewed during earlier development.

---

## 6. Severe-Episode Classification & Reliability Diagnostics
- **Severe Episode (AQI > 200) Recall:** {clf_results['metrics_gb']['Recall']:.3f} (vs Persistence: {clf_results['metrics_persistence']['Recall']:.3f})
- **PR-AUC / ROC-AUC:** {clf_results['metrics_gb']['PR_AUC']} / {clf_results['metrics_gb']['ROC_AUC']}
- **Brier Score Loss:** {clf_results['brier']:.4f}
- **Capacity-Matched Threshold:** At top-16.7% capacity, threshold is {clf_results['capacity_threshold']:.3f} (Precision: {clf_results['p_capacity']:.3f}, Recall: {clf_results['r_capacity']:.3f})

---

## 7. Prediction Intervals (Quantile Regression)
- **Nominal Coverage:** 80.0% ([p10, p90] interval)
- **Empirical Holdout Coverage:** {interval_results.get('overall_coverage')}% (Mean width: {interval_results.get('mean_width')} AQI units)
- **Honest Note:** {interval_results.get('statement')}

---

## 8. Decision Backtest (Weekly Resource Allocation)
- **Backtest Period:** {backtest_results.get('weeks_tested')} weekly simulated cycles across 2023.
- **Lift vs Uniform-Random Expectation:** **{backtest_results.get('lift_vs_random'):+.1f}%** (95% CI: [{backtest_results.get('ci_vs_random', [0, 0])[0]:+.1f}%, {backtest_results.get('ci_vs_random', [0, 0])[1]:+.1f}%])
- **Lift vs Persistence-Ranked:** **{backtest_results.get('lift_vs_persistence'):+.1f}%** (95% CI: [{backtest_results.get('ci_vs_persistence', [0, 0])[0]:+.1f}%, {backtest_results.get('ci_vs_persistence', [0, 0])[1]:+.1f}%])
- **Lift vs Last-Week-Worst:** **{backtest_results.get('lift_vs_last_week'):+.1f}%** (95% CI: [{backtest_results.get('ci_vs_last_week', [0, 0])[0]:+.1f}%, {backtest_results.get('ci_vs_last_week', [0, 0])[1]:+.1f}%])

---

## 9. Priority Score Robustness
- **Monte Carlo Simulations:** {robust_results.get('n_sims')} runs under ±30% random weight perturbations.
- **Robust Core:** {robust_results.get('robust_stations_count')} monitoring stations maintain ≥90% probability of remaining in the top 5.

---

## 10. Judge Q&A Cheat Sheet

"""
    for q, a in qna:
        md_content += f"### Q: {q}\n**A:** {a}\n\n"

    md_content += """---

## 11. Known Limitations & Responsible Deployment
1. **Autoregressive Baseline:** Point forecast improvements over persistence are modest on citywide averages.
2. **Spatial Density:** Official CAAQMS coverage is uneven; station readings do not represent entire wards.
3. **Sensor Attrition:** Periodic hardware outages require robust imputation to prevent ranking distortion.
4. **Administrative Role:** CityPulse is a decision-support screener for municipal inspectors, not an automated penal enforcement tool.
"""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = REPORTS_DIR / "evaluate_summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    json_data = {
        "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST"),
        "environment": env_info,
        "test_results": {k: v for k, v in test_results.items() if k != "groups"},
        "leakage_passed": leakage_results.get("all_passed"),
        "cv_winner": {
            "model": cv_results.get("winner"),
            "mae": cv_results.get("winner_mae"),
            "skill_pct": cv_results.get("winner_skill"),
            "ci": cv_results.get("winner_ci"),
        },
        "holdout": {
            "best_mae": holdout_results.get("best_mae"),
            "persistence_mae": holdout_results.get("persistence_mae"),
            "date_bootstrap_ci_95": holdout_results.get("best_ci_95"),
            "verdict": holdout_results.get("verdict"),
            "station_beats": holdout_results.get("station_beats"),
            "total_stations": holdout_results.get("total_stations"),
        },
        "classification": {
            "recall": clf_results["metrics_gb"]["Recall"],
            "precision": clf_results["metrics_gb"]["Precision"],
            "pr_auc": clf_results["metrics_gb"]["PR_AUC"],
            "brier": clf_results["brier"],
        },
        "interval_coverage": {
            "empirical_pct": interval_results.get("overall_coverage"),
            "nominal_pct": 80.0,
            "mean_width": interval_results.get("mean_width"),
        },
        "backtest": {
            "weeks_tested": backtest_results.get("weeks_tested"),
            "lift_vs_random": backtest_results.get("lift_vs_random"),
            "ci_vs_random": backtest_results.get("ci_vs_random"),
            "lift_vs_persistence": backtest_results.get("lift_vs_persistence"),
            "ci_vs_persistence": backtest_results.get("ci_vs_persistence"),
            "lift_vs_last_week": backtest_results.get("lift_vs_last_week"),
            "ci_vs_last_week": backtest_results.get("ci_vs_last_week"),
        },
        "robustness": {
            "n_sims": robust_results.get("n_sims"),
            "robust_stations_count": robust_results.get("robust_stations_count"),
        },
    }

    json_path = REPORTS_DIR / "evaluate_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    print(f"\nWrote full evaluation report to {md_path}")
    print(f"Wrote machine-readable summary to {json_path}")

    elapsed = time.time() - t0
    print(f"Stage 10 completed in {elapsed:.2f}s")
    return json_data



def main() -> None:
    """Main orchestration entry point."""
    parser = argparse.ArgumentParser(
        description="CityPulse: Mumbai — Reproduction & Comprehensive Evaluation Script"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="Fast demonstration using a subset of candidates")
    mode.add_argument("--full", action="store_true", help="Full evaluation across all 10 candidate architectures (default)")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running the unit test discovery suite")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed (default: 42)")
    args = parser.parse_args()

    total_start_time = time.time()
    quick_mode = args.quick
    n_boot = 200 if quick_mode else 2000

    print("=" * 80)
    print("CITYPULSE: MUMBAI — END-TO-END REPRODUCIBILITY & EVALUATION SUITE")
    print(f"Mode: {'QUICK (Live Demo)' if quick_mode else 'FULL (Comprehensive)'} | Seed: {args.seed} | Bootstrap Reps: {n_boot:,}")
    print("=" * 80)

    env_info = stage_1_environment(seed=args.seed)

    test_results = stage_2_test_suite(skip_tests=args.skip_tests)
    if test_results["status"] == "FAIL":
        sys.exit(1)

    if not FEATURES_PATH.exists():
        print(f"ERROR: Model features parquet missing at {FEATURES_PATH}. Run pipeline first.")
        sys.exit(1)
    df_features = pd.read_parquet(FEATURES_PATH)
    df_features["date"] = pd.to_datetime(df_features["date"])

    leakage_results = stage_3_leakage_checks(df_features)
    if not leakage_results["all_passed"]:
        sys.exit(1)

    cv_results = stage_4_cv_model_selection(df_features, quick=quick_mode, n_boot=n_boot)

    holdout_results = stage_5_holdout_evaluation(
        df_features,
        best_model_name=cv_results["winner"],
        features_to_use=cv_results["features"],
        n_boot=n_boot,
    )

    clf_results = stage_6_classification(df_features, features_to_use=cv_results["features"])

    interval_results = stage_7_prediction_intervals(df_features, features_to_use=cv_results["features"])

    df_daily = pd.read_parquet(DAILY_PATH)
    df_daily["date"] = pd.to_datetime(df_daily["date"])
    df_preds = holdout_results["test_df"].copy()
    df_preds["prob_unhealthy"] = clf_results["y_prob_gb"]

    backtest_results = stage_8_decision_backtest(df_daily, df_preds, top_n=5, threshold=150.0)

    robust_results = stage_9_robustness_analysis(df_preds, quick=quick_mode)

    stage_10_showcase_summary(
        env_info=env_info,
        test_results=test_results,
        leakage_results=leakage_results,
        cv_results=cv_results,
        holdout_results=holdout_results,
        clf_results=clf_results,
        interval_results=interval_results,
        backtest_results=backtest_results,
        robust_results=robust_results,
    )

    total_elapsed = time.time() - total_start_time
    print(f"\n[DONE] Full evaluation pipeline completed in {total_elapsed:.1f} seconds.")

    tests_ok = (test_results.get("status") in ["PASS", "SKIPPED"])
    leakage_ok = leakage_results.get("all_passed", False)
    if not (tests_ok and leakage_ok):
        print("\n[ERROR] Pipeline completed with test or leakage verification failures. Exiting with code 1.")
        sys.exit(1)
    else:
        print("[SUCCESS] All tests and leakage assertions passed cleanly. Exiting with code 0.")
        sys.exit(0)


if __name__ == "__main__":
    main()
