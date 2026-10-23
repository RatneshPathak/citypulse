"""CityPulse full evaluation: data-quality audit, EDA findings, rolling-origin validation,
sensitivity checks and integrity checks. Produces a report you can explain to judges.

Run from the project root (after src/forecast.py exists in the same folder):
    python src/evaluate.py

Reads  : data/citypulse_cleaned.csv
Writes : data/processed/evaluation_report.txt
         data/processed/rolling_monthly_results.csv
         data/processed/figures/*.png
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forecast as fc

OUT = "data/processed"
FIG = f"{OUT}/figures"
LINES = []

def say(s=""):
    print(s)
    LINES.append(str(s))

def section(title):
    say("\n" + "=" * 72)
    say(title)
    say("=" * 72)

def season(m):
    if m in (11, 12, 1, 2):
        return "Winter (Nov-Feb)"
    if m in (3, 4, 5):
        return "Summer (Mar-May)"
    if m in (6, 7, 8, 9):
        return "Monsoon (Jun-Sep)"
    return "Post-monsoon (Oct)"

def mae(a, b):
    return float(np.mean(np.abs(a - b)))

def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))

def audit(raw):
    section("1. DATA QUALITY AUDIT (hourly cleaned file)")
    say(f"Rows: {len(raw)}   Stations: {raw['Station'].nunique()}")
    say(f"Duplicate (station, hour) rows: {int(raw.duplicated(subset=['Station', 'From Date']).sum())}")
    rows = []
    for st, g in raw.groupby("Station"):
        g = g.sort_values("ts")
        span = int((g.ts.max() - g.ts.min()).total_seconds() // 3600) + 1
        s = g["PM2.5"].reset_index(drop=True)
        valid = s.dropna()
        same_prev = float((s == s.shift()).sum() / max(s.notna().sum(), 1) * 100)
        run_id = (s != s.shift()).cumsum()
        longest = int(s.groupby(run_id).transform("size").where(s.notna()).max())
        rows.append({
            "Station": st,
            "first": g.ts.min().date(), "last": g.ts.max().date(),
            "hours_present": len(g), "hours_expected": span,
            "hour_coverage_%": round(100 * len(g) / span, 1),
            "PM2.5_missing_%": round(s.isna().mean() * 100, 1),
            "PM10_missing_%": round(g["PM10"].isna().mean() * 100, 1),
            "NO2_missing_%": round(g["NO2"].isna().mean() * 100, 1),
            "SO2_missing_%": round(g["SO2"].isna().mean() * 100, 1),
            "PM2.5_negative": int((valid < 0).sum()),
            "PM2.5_p99.9": round(valid.quantile(0.999), 1),
            "PM2.5_max": round(valid.max(), 1),
            "same_as_prev_hour_%": round(same_prev, 1),
            "longest_identical_run_h": longest,
        })
    say(pd.DataFrame(rows).set_index("Station").T.to_string())
    say("\nHow to read: 'same_as_prev_hour_%' and 'longest_identical_run_h' help detect "
        "forward-filled or stuck-sensor values. Large values suggest filled/stuck data.")

def eda(raw, daily, figs):
    section("2. EXPLORATORY FINDINGS (daily station means, PM2.5 in ug/m3)")
    d = daily.dropna(subset=["PM2.5"]).copy()
    d["month"] = d["date"].dt.to_period("M")
    d["season"] = d["date"].dt.month.map(season)
    d["dow"] = d["date"].dt.day_name()
    d["above60"] = d["PM2.5"] > 60

    say("\nFINDING A - Stations differ:")
    t = d.groupby("Station").agg(days=("PM2.5", "count"), mean=("PM2.5", "mean"),
                                 median=("PM2.5", "median"),
                                 p95=("PM2.5", lambda x: x.quantile(0.95)),
                                 pct_days_above_60=("above60", lambda x: 100 * x.mean())).round(1)
    say(t.to_string())

    say("\nFINDING B - Strong seasonal pattern (mean PM2.5 by season and station):")
    s = d.pivot_table(index="season", columns="Station", values="PM2.5", aggfunc="mean").round(1)
    s["ALL STATIONS"] = d.groupby("season")["PM2.5"].mean().round(1)
    say(s.to_string())

    say("\nFINDING C - Weekday pattern (mean PM2.5, all stations):")
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    say(d.groupby("dow")["PM2.5"].mean().reindex(order).round(1).to_string())

    say("\nFINDING D - Time-of-day pattern (hourly mean PM2.5, all stations):")
    hr = raw.groupby(raw["ts"].dt.hour)["PM2.5"].mean().round(1)
    say(hr.to_string())

    say("\nFINDING E - Co-movement with other pollutants (daily correlation with PM2.5; "
        "correlation is NOT causation):")
    say(d[["PM2.5", "PM10", "NO2", "CO"]].corr()["PM2.5"].round(2).to_string())

    if figs:
        os.makedirs(FIG, exist_ok=True)
        m = d.pivot_table(index="month", columns="Station", values="PM2.5", aggfunc="mean")
        m.index = m.index.astype(str)
        m.plot(figsize=(10, 4), marker="o")
        plt.ylabel("Mean PM2.5 (ug/m3)")
        plt.title("Monthly mean PM2.5 by station")
        plt.xticks(rotation=60)
        plt.tight_layout()
        plt.savefig(f"{FIG}/monthly_pm25_by_station.png", dpi=150)
        plt.close()
        hr.plot(kind="bar", figsize=(10, 3.5))
        plt.ylabel("Mean PM2.5 (ug/m3)")
        plt.xlabel("Hour of day")
        plt.title("PM2.5 by hour of day (all stations)")
        plt.tight_layout()
        plt.savefig(f"{FIG}/pm25_by_hour.png", dpi=150)
        plt.close()

def rolling_eval(feats, cols, min_train_days=120):
    lab = feats.dropna(subset=["target", "pm_today"]).copy()
    lab["tm"] = lab["target_date"].dt.to_period("M")
    out, checks = [], 0
    for m in sorted(lab["tm"].unique()):
        start = m.to_timestamp()
        train = lab[lab["target_date"] < start]
        test = lab[lab["tm"] == m]
        if train["target_date"].nunique() < min_train_days or len(test) < 10:
            continue
        assert train["target_date"].max() < test["target_date"].min(), "temporal leakage!"
        checks += 1
        model = HistGradientBoostingRegressor(random_state=42, max_iter=200, learning_rate=0.05)
        model.fit(train[cols], train["target"])
        t = test.copy()
        t["pred_model"] = model.predict(test[cols])
        t["pred_persist"] = test["pm_today"]
        out.append(t)
    res = pd.concat(out) if out else pd.DataFrame()
    return res, checks

def detection(df, thr=60):
    y = df["target"] >= thr
    out = {}
    for name, col in (("model", "pred_model"), ("persistence", "pred_persist")):
        p = df[col] >= thr
        tp, fp, fn = int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum())
        out[name] = {"flagged_days": int(p.sum()), "true_high_days": int(y.sum()),
                     "precision": round(tp / (tp + fp), 2) if tp + fp else float("nan"),
                     "recall": round(tp / (tp + fn), 2) if tp + fn else float("nan")}
    return pd.DataFrame(out).T

def report_rolling(res, checks, figs):
    section("3. ROLLING-ORIGIN (walk-forward) VALIDATION - tests every month after enough history")
    if res.empty:
        say("Not enough data for rolling validation.")
        return
    say(f"Walk-forward folds run: {checks}. Each fold trains ONLY on target dates before the "
        f"test month (leakage assertion passed for every fold).")
    say(f"Pooled test rows: {len(res)}")
    say(f"\nPOOLED  model       MAE={mae(res.target, res.pred_model):.2f}  RMSE={rmse(res.target, res.pred_model):.2f}")
    say(f"POOLED  persistence MAE={mae(res.target, res.pred_persist):.2f}  RMSE={rmse(res.target, res.pred_persist):.2f}")

    res = res.copy()
    res["month"] = res["tm"].astype(str)
    res["season"] = res["target_date"].dt.month.map(season)
    res["err_model"] = (res.target - res.pred_model).abs()
    res["err_persist"] = (res.target - res.pred_persist).abs()

    mt = res.groupby("month").agg(n=("target", "size"), mean_pm25=("target", "mean"),
                                  MAE_model=("err_model", "mean"),
                                  MAE_persistence=("err_persist", "mean")).round(2)
    mt["better"] = np.where(mt["MAE_model"] < mt["MAE_persistence"], "model", "persistence")
    say("\nBy month:")
    say(mt.to_string())
    say(f"\nMonths where model beats persistence: {(mt['better'] == 'model').sum()} of {len(mt)}")
    mt.to_csv(f"{OUT}/rolling_monthly_results.csv")

    say("\nBy season:")
    say(res.groupby("season").agg(n=("target", "size"), mean_pm25=("target", "mean"),
                                  MAE_model=("err_model", "mean"),
                                  MAE_persistence=("err_persist", "mean")).round(2).to_string())

    res["level"] = pd.cut(res["target"], [-np.inf, 30, 60, np.inf],
                          labels=["<30 (Good)", "30-60", ">60 (Moderate or worse)"])
    say("\nBy actual PM2.5 level tomorrow (does it help when pollution is high?):")
    say(res.groupby("level", observed=True).agg(n=("target", "size"),
                                                MAE_model=("err_model", "mean"),
                                                MAE_persistence=("err_persist", "mean")).round(2).to_string())

    say("\nHigh-pollution day detection (actual PM2.5 >= 60 tomorrow; flag = forecast >= 60):")
    say(detection(res).to_string())

    if figs:
        os.makedirs(FIG, exist_ok=True)
        mt[["MAE_model", "MAE_persistence"]].plot(kind="bar", figsize=(10, 4))
        plt.ylabel("MAE (ug/m3)")
        plt.title("Walk-forward MAE by month: model vs persistence")
        plt.tight_layout()
        plt.savefig(f"{FIG}/rolling_mae_by_month.png", dpi=150)
        plt.close()

def sensitivity(cols):
    section("4. SENSITIVITY CHECK - minimum valid hours required per day")
    rows = []
    original = fc.MIN_HOURS
    for h in (12, 18, 22):
        fc.MIN_HOURS = h
        feats = fc.build_features(fc.load_daily())
        res, _ = rolling_eval(feats, cols)
        if res.empty:
            continue
        rows.append({"min_hours_per_day": h, "test_rows": len(res),
                     "MAE_model": round(mae(res.target, res.pred_model), 2),
                     "MAE_persistence": round(mae(res.target, res.pred_persist), 2)})
    fc.MIN_HOURS = original
    say(pd.DataFrame(rows).to_string(index=False))
    say("\nHow to read: if the conclusion (which method is better) stays the same across "
        "rows, the result is not an artefact of this one cleaning choice.")

def main():
    os.makedirs(OUT, exist_ok=True)
    raw = pd.read_csv(fc.DATA)
    raw["ts"] = pd.to_datetime(raw["From Date"], errors="coerce")
    raw = raw.dropna(subset=["ts"])

    audit(raw)
    daily = fc.load_daily()
    eda(raw, daily, figs=True)

    feats = fc.build_features(daily)
    cols = (["pm_today"] + [f"pm_lag{k}" for k in range(1, 7)]
            + ["pm_roll7", "pm10_today", "no2_today", "co_today", "dow", "month", "station_id"])
    res, checks = rolling_eval(feats, cols)
    report_rolling(res, checks, figs=True)
    sensitivity(cols)

    section("5. INTEGRITY STATEMENT (safe to say to judges)")
    say("- Features use only data up to day t; the target is day t+1.")
    say("- Every walk-forward fold trains only on dates earlier than its test month (asserted in code).")
    say("- The baseline (persistence) is evaluated on exactly the same rows as the model.")
    say("- The risk tier is a rule-based heuristic on PM2.5 categories, not a validated probability.")
    say("- Results come from 4 stations only and may not generalise city-wide.")

    with open(f"{OUT}/evaluation_report.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES))
    print(f"\nSaved report to {OUT}/evaluation_report.txt and charts to {FIG}/")

if __name__ == "__main__":
    main()