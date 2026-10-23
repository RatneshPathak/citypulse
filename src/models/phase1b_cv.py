"""Phase 1b model selection on 2021–2022 only. No holdout data is read."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.models.train_evaluate import FEATURES_PATH, _CV_FOLDS, get_feature_columns


REPORT_DIR = Path("reports")
PHASE1A_GROUPS = {
    "long_history": ["lag_14_aqi", "rolling_mean_14d", "rolling_std_14d"],
    "recent_change": ["aqi_delta_1d", "aqi_delta_7d"],
    "station_history": ["station_expanding_mean_aqi"],
    "calendar": ["month", "is_holi_window"],
}
OLD_FEATURES = [c for c in get_feature_columns() if c not in sum(PHASE1A_GROUPS.values(), [])]
ALPHAS = [0.1, 1.0, 10.0, 100.0]
INNER_WINDOWS = [
    ("2021-06-30", "2021-07-01", "2021-09-30"),
    ("2021-09-30", "2021-10-01", "2021-12-31"),
    ("2021-12-31", "2022-01-01", "2022-04-30"),
    ("2022-04-30", "2022-05-01", "2022-08-31"),
]
CANDIDATES = [
    "Persistence", "Ridge", "HistGB_L1", "LightGBM_L1", "LightGBM_Huber",
    "Ridge_Residual", "HistGB_L1_Residual", "LightGBM_L1_Residual",
    "LightGBM_Huber_Residual", "PerStation_LightGBM_L1",
]


def inner_date_splits(train: pd.DataFrame) -> list[tuple[np.ndarray, np.ndarray]]:
    dates = pd.to_datetime(train["date"])
    splits = []
    for train_end, test_start, test_end in INNER_WINDOWS:
        tr = np.flatnonzero((dates <= train_end).to_numpy())
        te = np.flatnonzero(((dates >= test_start) & (dates <= test_end)).to_numpy())
        if len(tr) and len(te):
            splits.append((tr, te))
    if len(splits) < 2:
        raise ValueError("At least two inner date splits are required")
    return splits


def ridge_pipeline(train: pd.DataFrame, features: list[str], residual: bool = False):
    baseline = train["lag_1_aqi"].to_numpy()
    target = train["target_next_day_aqi"].to_numpy() - baseline if residual else train["target_next_day_aqi"].to_numpy()
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", Ridge()),
    ])
    search = GridSearchCV(
        pipeline, {"model__alpha": ALPHAS}, cv=inner_date_splits(train),
        scoring="neg_mean_absolute_error", refit=True, n_jobs=1,
    )
    search.fit(train[features], target)
    return search.best_estimator_, float(search.best_params_["model__alpha"])


def make_model(name: str):
    if name.startswith("HistGB"):
        return HistGradientBoostingRegressor(
            loss="absolute_error", max_iter=150, learning_rate=0.06,
            max_depth=6, l2_regularization=1.0, random_state=42,
        )
    if name.startswith("LightGBM") or name.startswith("PerStation"):
        objective = "huber" if "Huber" in name else "regression_l1"
        return LGBMRegressor(
            objective=objective, n_estimators=120, learning_rate=0.05,
            num_leaves=12, min_child_samples=40, reg_lambda=1.0,
            random_state=42, n_jobs=2, verbosity=-1, deterministic=True,
        )
    raise ValueError(name)


def fit_predict(name: str, train: pd.DataFrame, test: pd.DataFrame, features: list[str]):
    if name == "Persistence":
        return test["lag_1_aqi"].to_numpy(), {}
    residual = name.endswith("_Residual")
    if name.startswith("Ridge"):
        model, alpha = ridge_pipeline(train, features, residual)
        prediction = model.predict(test[features])
        return prediction + test["lag_1_aqi"].to_numpy() if residual else prediction, {"alpha": alpha}
    if name == "PerStation_LightGBM_L1":
        pooled = make_model(name)
        pooled.fit(train[features], train["target_next_day_aqi"])
        prediction = np.asarray(pooled.predict(test[features]))
        station_models = 0
        for station, station_train in train.groupby("canonical_station"):
            station_test = test["canonical_station"] == station
            if len(station_train) < 250 or not station_test.any():
                continue
            model = make_model(name)
            model.fit(station_train[features], station_train["target_next_day_aqi"])
            prediction[station_test.to_numpy()] = model.predict(test.loc[station_test, features])
            station_models += 1
        return prediction, {"station_models": station_models, "fallback": "pooled LightGBM-L1"}
    model = make_model(name)
    y = train["target_next_day_aqi"].to_numpy()
    if residual:
        y = y - train["lag_1_aqi"].to_numpy()
    model.fit(train[features], y)
    prediction = np.asarray(model.predict(test[features]))
    if residual:
        prediction += test["lag_1_aqi"].to_numpy()
    return prediction, {}


def season_for(dates: pd.Series) -> pd.Series:
    month = pd.to_datetime(dates).dt.month
    return pd.Series(np.select(
        [month.isin([12, 1, 2]), month.isin([3, 4, 5]), month.isin([6, 7, 8, 9])],
        ["winter", "summer", "monsoon"], default="post_monsoon",
    ), index=dates.index)


def evaluate_cv(df: pd.DataFrame, features: list[str], names: list[str]):
    rows = []
    params = {}
    for fold in _CV_FOLDS:
        dates = df["date"]
        train = df[(dates >= fold["train_start"]) & (dates <= fold["train_end"])].reset_index(drop=True)
        test = df[(dates >= fold["test_start"]) & (dates <= fold["test_end"])].reset_index(drop=True)
        if train.empty or test.empty:
            raise ValueError(f"Empty outer fold: {fold['name']}")
        fold_frame = test[["date", "canonical_station", "target_next_day_aqi", "lag_1_aqi"]].copy()
        fold_frame["fold"] = fold["name"]
        fold_frame["season"] = season_for(fold_frame["date"])
        for name in names:
            prediction, details = fit_predict(name, train, test, features)
            fold_frame[name] = prediction
            params.setdefault(name, []).append(details)
        rows.append(fold_frame)
    return pd.concat(rows, ignore_index=True), params


def date_bootstrap_ci(frame: pd.DataFrame, candidate: str, n_boot: int = 2000, seed: int = 42):
    grouped = frame.assign(
        model_error=np.abs(frame["target_next_day_aqi"] - frame[candidate]),
        base_error=np.abs(frame["target_next_day_aqi"] - frame["Persistence"]),
    ).groupby("date")[["model_error", "base_error"]].agg(["sum", "count"])
    model_sum = grouped[("model_error", "sum")].to_numpy()
    base_sum = grouped[("base_error", "sum")].to_numpy()
    counts = grouped[("model_error", "count")].to_numpy()
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(grouped), size=(n_boot, len(grouped)))
    differences = (model_sum[samples].sum(axis=1) - base_sum[samples].sum(axis=1)) / counts[samples].sum(axis=1)
    return [float(v) for v in np.quantile(differences, [0.025, 0.975])]


def summarize(frame: pd.DataFrame, names: list[str]):
    actual = frame["target_next_day_aqi"]
    pooled = []
    folds = []
    seasons = []
    for name in names:
        mae = mean_absolute_error(actual, frame[name])
        base_mae = mean_absolute_error(actual, frame["Persistence"])
        pooled.append({"model": name, "n": len(frame), "MAE": round(mae, 3),
                       "skill_pct": round(100 * (1 - mae / base_mae), 2),
                       "date_bootstrap_CI_MAE_diff": [round(x, 3) for x in date_bootstrap_ci(frame, name)]})
        for column, output in [("fold", folds), ("season", seasons)]:
            for group, subset in frame.groupby(column):
                group_mae = mean_absolute_error(subset["target_next_day_aqi"], subset[name])
                group_base = mean_absolute_error(subset["target_next_day_aqi"], subset["Persistence"])
                output.append({column: group, "model": name, "n": len(subset), "MAE": round(group_mae, 3),
                               "skill_pct": round(100 * (1 - group_mae / group_base), 2)})
    return pooled, folds, seasons


def markdown_table(rows: list[dict], columns: list[str]) -> str:
    return "| " + " | ".join(columns) + " |\n| " + " | ".join(["---"] * len(columns)) + " |\n" + "".join(
        "| " + " | ".join(str(row[column]) for column in columns) + " |\n" for row in rows
    )


def run_ablation(df: pd.DataFrame):
    results = []
    for group, added in [("old", []), *PHASE1A_GROUPS.items()]:
        frame, params = evaluate_cv(df, OLD_FEATURES + added, ["Persistence", "Ridge"])
        pooled, _, _ = summarize(frame, ["Ridge"])
        results.append({"group": group, "features": len(OLD_FEATURES + added),
                        "MAE": pooled[0]["MAE"], "alpha_by_fold": [x["alpha"] for x in params["Ridge"]]})
    old_mae = results[0]["MAE"]
    retained = [group for group, row in zip(PHASE1A_GROUPS, results[1:]) if row["MAE"] < old_mae]
    return results, retained


def run_candidates(df: pd.DataFrame, retained: list[str]):
    features = OLD_FEATURES + [column for group in retained for column in PHASE1A_GROUPS[group]]
    frame, params = evaluate_cv(df, features, CANDIDATES)
    pooled, folds, seasons = summarize(frame, CANDIDATES)
    winner = min(pooled, key=lambda row: row["MAE"])["model"]
    return {"features": features, "retained_groups": retained, "candidates": CANDIDATES,
            "config_count": len(CANDIDATES), "lightgbm_config_count": 5,
            "winner": winner, "pooled": pooled, "folds": folds, "seasons": seasons,
            "params_by_fold": params}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["ablation", "candidates"], required=True)
    args = parser.parse_args()
    df = pd.read_parquet(FEATURES_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= "2021-01-01") & (df["date"] <= "2022-12-31")].copy()
    if df.empty:
        raise ValueError("No 2021–2022 training rows")
    missing = set(get_feature_columns()) - set(df.columns)
    if missing:
        raise ValueError(f"Missing Phase 1a columns: {sorted(missing)}")
    REPORT_DIR.mkdir(exist_ok=True)
    ablation, retained = run_ablation(df)
    (REPORT_DIR / "phase1b_ablation.json").write_text(
        json.dumps({"ablation": ablation, "retained_groups": retained}, indent=2) + "\n", encoding="utf-8"
    )
    print(markdown_table(ablation, ["group", "features", "MAE", "alpha_by_fold"]))
    print("Retained groups:", retained)
    if args.stage == "ablation":
        return
    result = run_candidates(df, retained)
    (REPORT_DIR / "phase1b_cv.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    sections = [
        "# Phase 1b CV-only evaluation (2021–2022)",
        "Three expanding outer folds; Ridge alpha is tuned on inner date splits inside each outer training fold.",
        "Bootstrap resamples dates (all station rows for a sampled date together); 2,000 replicates, seed 42.",
        f"Candidate configurations: {result['config_count']} total, including {result['lightgbm_config_count']} LightGBM variants. Parameters were fixed before results were viewed.",
        f"Retained Phase 1a groups: {', '.join(retained) if retained else 'none'}.",
        "## Ablation", markdown_table(ablation, ["group", "features", "MAE", "alpha_by_fold"]),
        "## Pooled", markdown_table(result["pooled"], ["model", "n", "MAE", "skill_pct", "date_bootstrap_CI_MAE_diff"]),
        "## Per fold", markdown_table(result["folds"], ["fold", "model", "n", "MAE", "skill_pct"]),
        "## Per season", markdown_table(result["seasons"], ["season", "model", "n", "MAE", "skill_pct"]),
        f"CV-selected model: **{result['winner']}**. The 2023 holdout has not been run for Phase 1b.",
    ]
    (REPORT_DIR / "phase1b_cv.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print("\n".join(sections))


if __name__ == "__main__":
    main()
