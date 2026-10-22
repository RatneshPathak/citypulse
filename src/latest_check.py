"""Streamlit view: latest-data check for the 4 Mumbai stations (2025-2026 data).

Reads the real outputs of src/persistence_forecast.py (written to data/processed/):
  latest_forecast.csv, daily_history.csv, persistence_metrics.json,
  evaluation_report.txt, figures/*.png
Nothing here is hardcoded or simulated. If the files are absent, an empty state is shown.

Changes versus the recovered first version:
  * data-health section (latest observation date, target date, stations available, completeness)
  * explicit file-read / missing-column / stale-output messages (find_dir no longer fails silently)
  * station_warnings() and coverage_for_level() helpers, reused by action_centre.py
"""
import json
from pathlib import Path

import pandas as pd

from knowledge_content import actions_for_tier

CANDIDATE_DIRS = [Path("four_station_check/data/processed"), Path("data/processed")]
REQUIRED = {"station", "station_short", "as_of_date", "forecast_for_date", "estimate_pm25",
            "low_80", "high_80", "tier_heuristic", "tier_at_upper_bound", "suggested_action"}
TIER_COLOR = {"Good": "green", "Satisfactory": "blue", "Moderate": "orange",
              "Poor": "red", "Very Poor": "violet", "Severe": "gray"}
LOW_COVERAGE_WARN = 0.70
MIN_HOURS_OK = 18       # same minimum valid hours per day used by the pipeline's main analysis
STALE_DAYS = 2
WINDOW_DAYS = 30
RUN_HINT = "python src/persistence_forecast.py"


def locate(base=Path(".")):
    """Return (directory or None, list of problems found while looking)."""
    problems = []
    for d in CANDIDATE_DIRS:
        f = Path(base) / d / "latest_forecast.csv"
        if not f.exists():
            continue
        try:
            cols = set(pd.read_csv(f, nrows=0).columns)
        except Exception as e:
            problems.append(f"{f} exists but could not be read ({type(e).__name__}: {e}).")
            continue
        missing = REQUIRED - cols
        if missing:
            problems.append(f"{f} is missing expected columns: {', '.join(sorted(missing))}. "
                            f"Regenerate it with `{RUN_HINT}`.")
            continue
        return Path(base) / d, problems
    return None, problems


def find_dir(base=Path(".")):
    return locate(base)[0]


def load_latest(base=Path(".")):
    """Always returns a dict. data['dir'] is None when no valid output folder exists."""
    d, problems = locate(base)
    out = {"dir": d, "latest": pd.DataFrame(), "history": pd.DataFrame(), "metrics": {},
           "report": "", "figures": [], "problems": problems}
    if d is None:
        return out
    lf = pd.read_csv(d / "latest_forecast.csv")
    for c in ("as_of_date", "forecast_for_date", "latest_data_timestamp"):
        if c in lf.columns:
            lf[c] = pd.to_datetime(lf[c], errors="coerce")
    out["latest"] = lf

    hp = d / "daily_history.csv"
    if hp.exists():
        try:
            hist = pd.read_csv(hp)
            if "date" in hist.columns:
                hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
                hist = hist.dropna(subset=["date"])
            out["history"] = hist
        except Exception as e:
            out["problems"].append(f"daily_history.csv could not be read ({type(e).__name__}: {e}). "
                                   f"Trend charts and completeness checks are unavailable.")
    else:
        out["problems"].append("daily_history.csv not found. Trend charts and completeness checks are unavailable.")

    mp = d / "persistence_metrics.json"
    if mp.exists():
        try:
            out["metrics"] = json.loads(mp.read_text())
        except Exception as e:
            out["problems"].append(f"persistence_metrics.json is not valid JSON ({e}). "
                                   f"Evidence panel is unavailable; rerun `{RUN_HINT}`.")
    else:
        out["problems"].append("persistence_metrics.json not found. Evidence panel is unavailable.")

    rp = d / "evaluation_report.txt"
    out["report"] = rp.read_text(errors="replace") if rp.exists() else ""
    out["figures"] = sorted((d / "figures").glob("*.png")) if (d / "figures").exists() else []
    return out


def coverage_table(metrics):
    rows = []
    for level, v in (metrics.get("coverage_by_level") or {}).items():
        rows.append({"Today's PM2.5 level (ug/m3)": level, "Days": v.get("n"),
                     "Measured coverage": v.get("coverage"), "MAE (ug/m3)": v.get("MAE")})
    return pd.DataFrame(rows)


def low_coverage_levels(metrics):
    return [(lvl, v) for lvl, v in (metrics.get("coverage_by_level") or {}).items()
            if v.get("coverage") is not None and v["coverage"] < LOW_COVERAGE_WARN]


def coverage_for_level(metrics, value):
    """Return (level_label, stats) for the measured-coverage bin containing `value`, or None."""
    for label, v in (metrics.get("coverage_by_level") or {}).items():
        try:
            lo, hi = [float(x) for x in label.strip("[)").split(",")]
        except ValueError:
            continue
        if lo <= value < hi:
            return label, v
    return None


def data_health(lf, hist):
    """Per-station completeness table from the real outputs. No simulated values."""
    as_of = lf["as_of_date"].max() if "as_of_date" in lf.columns else pd.NaT
    rows = []
    for _, r in lf.iterrows():
        row = {"station": r["station"], "station_short": r["station_short"],
               "hours_today": r.get("hours_used_today", float("nan")),
               "days_behind": r.get("days_behind_latest_station", float("nan")),
               "days_with_value": None, "missing_days": None, "low_hour_days": None}
        if not hist.empty and {"station", "date"} <= set(hist.columns) and pd.notna(as_of):
            h = hist[(hist["station"] == r["station"])
                     & (hist["date"] > as_of - pd.Timedelta(days=WINDOW_DAYS))
                     & (hist["date"] <= as_of)]
            row["days_with_value"] = int(h["date"].nunique())
            row["missing_days"] = WINDOW_DAYS - row["days_with_value"]
            if "n_hours" in h.columns:
                row["low_hour_days"] = int((h["n_hours"] < MIN_HOURS_OK).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def station_warnings(health_row):
    """Plain-language data-quality warnings for one station (a row of data_health)."""
    w = []
    hrs = health_row.get("hours_today")
    if pd.notna(hrs) and hrs < MIN_HOURS_OK:
        w.append(f"Only {int(hrs)} of 24 hours were valid on the latest day, so today's value is less reliable.")
    behind = health_row.get("days_behind")
    if pd.notna(behind) and behind > 0:
        w.append(f"This station's latest reading is {int(behind)} day(s) older than the newest station.")
    miss = health_row.get("missing_days")
    if miss is not None and pd.notna(miss) and miss >= 5:
        w.append(f"{int(miss)} of the last {WINDOW_DAYS} days have no usable daily value.")
    return w


def snapshot_age_days(lf):
    as_of = lf["as_of_date"].max()
    if pd.isna(as_of):
        return None
    return (pd.Timestamp.today().normalize() - as_of).days


def _fmt_date(ts):
    return "unknown" if pd.isna(ts) else f"{ts:%d %b %Y}"


def _trend_chart(st, hist, row, days=120):
    if hist.empty or "station" not in hist.columns:
        st.info("No daily history available for this station.")
        return
    h = hist[hist["station"] == row["station"]].sort_values("date").tail(days)
    if h.empty:
        st.info("No daily history available for this station.")
        return
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.line_chart(h.set_index("date")["pm25_daily_mean"])
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=h["date"], y=h["pm25_daily_mean"], mode="lines", name="Daily mean PM2.5"))
    if pd.notna(row["forecast_for_date"]):
        fig.add_trace(go.Scatter(
            x=[row["forecast_for_date"]] * 2, y=[row["low_80"], row["high_80"]], mode="lines",
            name="80% empirical range", line=dict(width=6)))
        fig.add_trace(go.Scatter(
            x=[row["forecast_for_date"]], y=[row["estimate_pm25"]], mode="markers",
            name="Next-day estimate", marker=dict(size=10, symbol="diamond")))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10),
                      yaxis_title="PM2.5 (ug/m3)", legend=dict(orientation="h"))
    st.plotly_chart(fig)


def render_data_health(st, data):
    lf, hist = data["latest"], data["history"]
    as_of = lf["as_of_date"].max()
    target = lf["forecast_for_date"].max()
    n_now = len(lf)
    n_expected = hist["station"].nunique() if (not hist.empty and "station" in hist.columns) else n_now
    n_expected = max(n_expected, n_now)

    st.markdown("##### Data health")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest observation date", _fmt_date(as_of))
    c2.metric("Forecast target date", _fmt_date(target))
    c3.metric("Stations with an estimate", f"{n_now} of {n_expected}")
    files_ok = sum([not lf.empty, not hist.empty, bool(data["metrics"])])
    c4.metric("Core output files read", f"{files_ok} of 3")
    st.caption("Latest observation date is the last day with enough valid hours. "
               "The target date is the next day. This is a stored snapshot, not a live feed.")

    for p in data["problems"]:
        st.warning(p)
    if n_now < n_expected:
        st.warning(f"Only {n_now} of {n_expected} stations have a current estimate.")

    health = data_health(lf, hist)
    if health.empty:
        return health
    show = health.rename(columns={
        "station_short": "Station", "hours_today": "Valid hours on latest day",
        "days_behind": "Days behind newest station", "days_with_value": f"Days with a value (last {WINDOW_DAYS})",
        "missing_days": f"Days without a value (last {WINDOW_DAYS})",
        "low_hour_days": f"Days under {MIN_HOURS_OK} valid hours (last {WINDOW_DAYS})"}).drop(columns="station")
    st.dataframe(show, hide_index=True)
    for _, hr in health.iterrows():
        for msg in station_warnings(hr):
            st.warning(f"{hr['station_short']}: {msg}")
    return health


def render_latest_check(base=Path(".")):
    import streamlit as st

    st.subheader("Latest-data check: next-day PM2.5 estimate, 4 stations (2025-2026 data)")
    st.caption("Supplementary dataset, separate from any 2021-2023 replay elsewhere in the app. "
               "Persistence estimate with empirical error bands. Educational prototype, not an official CPCB forecast.")

    data = load_latest(base)
    if data["dir"] is None:
        for p in data["problems"]:
            st.error(p)
        st.info(f"The 4-station outputs were not found. Run `{RUN_HINT}` "
                "from the repository root, then reload this page.")
        return

    lf, hist, metrics = data["latest"], data["history"], data["metrics"]
    if lf.empty:
        st.warning("latest_forecast.csv is empty.")
        return

    as_of = lf["as_of_date"].max()
    age = snapshot_age_days(lf)
    st.info(f"Stored snapshot, not a live feed. Latest usable day: {_fmt_date(as_of)}"
            + ("" if age is None else f" ({age} day(s) before today)") + ".", icon=":material/schedule:")
    if age is not None and age > STALE_DAYS:
        st.warning(f"This snapshot is more than {STALE_DAYS} days old. Treat the estimates as stale.")

    render_data_health(st, data)

    st.markdown("##### Station estimates")
    ranked = lf.sort_values(["estimate_pm25", "high_80"], ascending=False).reset_index(drop=True)
    cols = st.columns(len(ranked))
    for col, (_, r) in zip(cols, ranked.iterrows()):
        with col:
            with st.container(border=True):
                st.markdown(f"**{r['station_short']}**")
                st.metric(f"Estimate for {_fmt_date(r['forecast_for_date'])}", f"{r['estimate_pm25']:.0f} ug/m3")
                st.caption(f"80% range: {r['low_80']:.0f} to {r['high_80']:.0f}")
                st.markdown(f"Heuristic tier: :{TIER_COLOR.get(r['tier_heuristic'], 'gray')}[**{r['tier_heuristic']}**]")
                if r["tier_at_upper_bound"] != r["tier_heuristic"]:
                    st.caption(f"Upper bound reaches {r['tier_at_upper_bound']}")

    show = ranked[["station_short", "estimate_pm25", "low_80", "high_80", "tier_heuristic",
                   "tier_at_upper_bound", "suggested_action"]].rename(columns={
        "station_short": "Station", "estimate_pm25": "Estimate", "low_80": "Low (80%)",
        "high_80": "High (80%)", "tier_heuristic": "Tier (heuristic)",
        "tier_at_upper_bound": "Tier at upper bound", "suggested_action": "Suggested action (review)"})
    st.dataframe(show, hide_index=True)
    st.caption("Estimate = today's daily mean PM2.5. The tier is a heuristic PM2.5 category, not a probability. "
               "Ranges are not guarantees. Suggested actions are illustrative prompts for human review.")

    st.markdown("##### Station detail")
    name = st.selectbox("Station", list(ranked["station_short"]), key="lc_station")
    row = ranked[ranked["station_short"] == name].iloc[0]
    _trend_chart(st, hist, row)
    st.markdown(f"**Suggested action (for review):** {row['suggested_action']}")
    related = [a["name"] for a in actions_for_tier(row["tier_at_upper_bound"])]
    st.caption("Related library entries (see Action Centre tab): " + "; ".join(related))
    if "latest_data_timestamp" in row.index and pd.notna(row["latest_data_timestamp"]):
        if "hours_used_today" in row.index and pd.notna(row["hours_used_today"]):
            st.caption(f"Latest raw reading for this station: {row['latest_data_timestamp']:%d %b %Y %H:%M}. "
                       f"Daily value uses {int(row['hours_used_today'])} valid hours.")
        else:
            st.caption(f"Latest raw reading for this station: {row['latest_data_timestamp']:%d %b %Y %H:%M}.")

    st.markdown("##### Evidence: how the bands performed (walk-forward, measured)")
    if metrics:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Nominal coverage", f"{metrics.get('nominal_coverage', float('nan')):.0%}")
        m2.metric("Measured coverage", f"{metrics.get('empirical_coverage', float('nan')):.1%}")
        m3.metric("Persistence MAE", f"{metrics.get('persistence_MAE', float('nan')):.2f} ug/m3")
        m4.metric("Mean band width", f"{metrics.get('mean_band_width', float('nan')):.1f} ug/m3")
        st.caption(f"{metrics.get('n_predictions', '?')} walk-forward predictions from {metrics.get('eval_start', '?')}. "
                   "Each band uses only past data (no leakage).")
        ct = coverage_table(metrics)
        if not ct.empty:
            st.dataframe(ct, hide_index=True)
        for lvl, v in low_coverage_levels(metrics):
            st.warning(f"Bands are unreliable for days with today's PM2.5 in {lvl}: measured coverage "
                       f"{v['coverage']:.0%} on {v['n']} days (small sample). Treat estimates at this level with caution.")
    else:
        st.info("persistence_metrics.json not found or unreadable. See the data-health warnings above.")

    if data["report"]:
        with st.expander("Full evaluation report (machine-learning model vs persistence baselines)"):
            st.code(data["report"])
    for fig in data["figures"]:
        with st.expander(f"Figure: {fig.stem.replace('_', ' ')}"):
            st.image(str(fig))

    with st.expander("Limitations of this check"):
        st.markdown(
            "- Only 4 stations and under two years of data; results may not generalise.\n"
            "- Persistence is a baseline: it cannot anticipate sudden changes.\n"
            "- Tiers are heuristic PM2.5 categories, not an official AQI or a probability.\n"
            "- Isolated sensor spikes were kept in the data, not removed.\n"
            "- This is a stored snapshot; there is no automatic live update pipeline.\n"
            "- Correlation between pollutants does not establish causes."
        )
