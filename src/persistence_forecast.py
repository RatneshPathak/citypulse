"""CityPulse: next-day PM2.5 estimate = today's daily mean (persistence), with
empirical error bands measured from past data and a HEURISTIC risk tier.

Why persistence: in our walk-forward test the gradient-boosting model did not
beat it (see data/processed/evaluation_report.txt). This is reported honestly.

Outputs (data/processed/):
  latest_forecast.csv        one row per station, read by the UI
  daily_history.csv          daily means per station, for the trend chart
  persistence_walkforward.csv  every walk-forward prediction (audit trail)
  persistence_metrics.json   measured coverage / error numbers
Run from repo root:  python src/persistence_forecast.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "citypulse_cleaned.csv"
OUT = ROOT / "data" / "processed"

MIN_HOURS = 18                      # valid hours needed for a usable day
BIN_EDGES = [0, 30, 60, 90, np.inf]  # bands are estimated per today's-level bin
MIN_N = 40                          # min past days per bin, else merge with lower bin
Q_LO, Q_HI = 0.10, 0.90             # nominal 80% band
EVAL_START = pd.Timestamp("2025-07-01")  # first target date scored walk-forward
HIGH = 60                           # "high day" threshold used for detection stats

# Heuristic PM2.5 category cut-offs (ug/m3). VERIFY against the CPCB document
# and cite it in DATA_STATEMENT.md. This is NOT the full AQI and NOT a probability.
TIERS = [(30, "Good"), (60, "Satisfactory"), (90, "Moderate"),
         (120, "Poor"), (250, "Very Poor"), (np.inf, "Severe")]
TIER_ORDER = [n for _, n in TIERS]

# Illustrative suggestions for the decision interface, NOT official guidance.
ACTIONS = {
    "Good": "Routine monitoring.",
    "Satisfactory": "Routine monitoring.",
    "Moderate": "Watchlist: check local dust/construction/burning sources.",
    "Poor": "Prioritise: inspections and dust control; issue public advisory.",
    "Very Poor": "High priority: targeted enforcement and health advisory.",
    "Severe": "Top priority: emergency measures and health advisory.",
}


def tier(x):
    for cut, name in TIERS:
        if x <= cut:
            return name


def load_daily():
    df = pd.read_csv(DATA, parse_dates=["From Date", "To Date"])
    df["date"] = df["From Date"].dt.normalize()
    daily = (df.groupby(["Station", "date"])["PM2.5"]
               .agg(pm25="mean", n_hours="count").reset_index())
    daily = daily[daily["n_hours"] >= MIN_HOURS].copy()
    last_ts = df.dropna(subset=["PM2.5"]).groupby("Station")["To Date"].max()
    return daily, last_ts


def make_pairs(daily):
    rows = []
    for st, g in daily.groupby("Station"):
        s = g.set_index("date")["pm25"].asfreq("D")
        p = pd.DataFrame({"today": s, "target": s.shift(-1)}).dropna()
        p["Station"] = st
        p["date"] = p.index
        rows.append(p.reset_index(drop=True))
    out = pd.concat(rows, ignore_index=True)
    out["target_date"] = out["date"] + pd.Timedelta(days=1)
    out["resid"] = out["target"] - out["today"]
    return out


def band(hist, level):
    """Residual quantiles from past (today, tomorrow) pairs with similar level."""
    i = min(int(np.searchsorted(BIN_EDGES, level, side="right")) - 1,
            len(BIN_EDGES) - 2)
    i = max(i, 0)
    hi_edge, lo_i = BIN_EDGES[i + 1], i
    while True:
        m = (hist["today"] >= BIN_EDGES[lo_i]) & (hist["today"] < hi_edge)
        if m.sum() >= MIN_N or lo_i == 0:
            break
        lo_i -= 1
    basis = f"past days with today's PM2.5 in [{BIN_EDGES[lo_i]}, {hi_edge})"
    if m.sum() < MIN_N:          # even the merged bins are thin: use everything
        m = pd.Series(True, index=hist.index)
        basis = "all past days (too few similar-level days)"
    if m.sum() < 5:
        return None
    r = hist.loc[m, "resid"]
    return (float(np.quantile(r, Q_LO)), float(np.quantile(r, Q_HI)),
            int(m.sum()), basis)


def walk_forward(pairs):
    rows = []
    for _, r in pairs[pairs["target_date"] >= EVAL_START].iterrows():
        # only outcomes already known at the end of day r.date (no leakage)
        hist = pairs[pairs["target_date"] <= r["date"]]
        b = band(hist, r["today"])
        if b is None:
            continue
        lo, hi = max(0.0, r["today"] + b[0]), r["today"] + b[1]
        rows.append(dict(Station=r["Station"], date=r["date"], today=r["today"],
                         target=r["target"], low=lo, high=hi, n_band=b[2]))
    wf = pd.DataFrame(rows)
    wf["covered"] = (wf["target"] >= wf["low"]) & (wf["target"] <= wf["high"])
    wf["abs_err"] = (wf["target"] - wf["today"]).abs()
    wf["level_bin"] = pd.cut(wf["today"], BIN_EDGES, right=False)
    return wf


def metrics(wf):
    th, pr = wf["today"] >= HIGH, wf["target"] >= HIGH
    tp = int((th & pr).sum())
    m = {
        "n_predictions": int(len(wf)),
        "eval_start": str(EVAL_START.date()),
        "nominal_coverage": Q_HI - Q_LO,
        "empirical_coverage": round(float(wf["covered"].mean()), 3),
        "mean_band_width": round(float((wf["high"] - wf["low"]).mean()), 1),
        "persistence_MAE": round(float(wf["abs_err"].mean()), 2),
        "persistence_RMSE": round(float(np.sqrt((wf["abs_err"] ** 2).mean())), 2),
        "high_day_precision": round(tp / max(int(th.sum()), 1), 2),
        "high_day_recall": round(tp / max(int(pr.sum()), 1), 2),
        "coverage_by_level": {
            str(k): {"n": int(len(g)), "coverage": round(float(g["covered"].mean()), 3),
                     "MAE": round(float(g["abs_err"].mean()), 2)}
            for k, g in wf.groupby("level_bin", observed=True)},
    }
    return m


def latest(daily, last_ts, pairs):
    data_end = daily["date"].max()
    rows = []
    for st, g in daily.groupby("Station"):
        g = g.sort_values("date")
        r = g.iloc[-1]
        b = band(pairs, r["pm25"])
        lo, hi = max(0.0, r["pm25"] + b[0]), r["pm25"] + b[1]
        t_est, t_hi = tier(r["pm25"]), tier(hi)
        action = ACTIONS[t_est]
        if TIER_ORDER.index(t_hi) > TIER_ORDER.index(t_est):
            action += f" Upper bound reaches {t_hi}: pre-position resources."
        rows.append(dict(
            station=st, station_short=st.split(",")[0],
            as_of_date=r["date"].date(),
            forecast_for_date=(r["date"] + pd.Timedelta(days=1)).date(),
            latest_data_timestamp=last_ts[st],
            days_behind_latest_station=int((data_end - r["date"]).days),
            hours_used_today=int(r["n_hours"]),
            todays_pm25=round(r["pm25"], 1), estimate_pm25=round(r["pm25"], 1),
            low_80=round(lo, 1), high_80=round(hi, 1),
            tier_heuristic=t_est, tier_at_upper_bound=t_hi,
            suggested_action=action, n_days_in_band=b[2], band_basis=b[3],
            method_note="Persistence estimate (tomorrow = today). Band = 10th-90th "
                        "percentile of past day-to-day changes. Tier is a heuristic "
                        "PM2.5 category, not a probability."))
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    daily, last_ts = load_daily()
    pairs = make_pairs(daily)
    wf = walk_forward(pairs)
    m = metrics(wf)
    lf = latest(daily, last_ts, pairs)

    daily.rename(columns={"Station": "station", "pm25": "pm25_daily_mean"}) \
         .to_csv(OUT / "daily_history.csv", index=False)
    wf.drop(columns="level_bin").to_csv(OUT / "persistence_walkforward.csv", index=False)
    lf.to_csv(OUT / "latest_forecast.csv", index=False)
    (OUT / "persistence_metrics.json").write_text(json.dumps(m, indent=2))

    print(json.dumps(m, indent=2))
    print(lf[["station_short", "as_of_date", "estimate_pm25", "low_80",
              "high_80", "tier_heuristic", "tier_at_upper_bound"]].to_string(index=False))


if __name__ == "__main__":
    main()