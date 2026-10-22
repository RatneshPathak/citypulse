"""Streamlit view: station-level Action Centre.

Reads the real latest_forecast.csv / daily_history.csv / persistence_metrics.json via latest_check
and pairs each station with entries from the action library (knowledge_content.py).
All actions are advisory. No source of pollution is identified or confirmed here.
"""
from pathlib import Path

import pandas as pd

from knowledge_content import actions_for_tier
from latest_check import (RUN_HINT, STALE_DAYS, TIER_COLOR, _fmt_date, coverage_for_level,
                          data_health, load_latest, snapshot_age_days, station_warnings)

LIMITATIONS = [
    "Persistence estimate: tomorrow is assumed to look like today. It cannot see sudden changes.",
    "The 80% range is empirical and not a guarantee; some outcomes will fall outside it.",
    "Tiers are heuristic PM2.5 categories, not probabilities and not the official overall AQI.",
    "PM2.5 alone cannot identify a pollution source. Any source named by staff needs on-site confirmation.",
    "Only four stations are covered, so this does not describe the rest of Mumbai.",
]


def _actions_for(row):
    seen, out = set(), []
    for tier in (row["tier_heuristic"], row["tier_at_upper_bound"]):
        for a in actions_for_tier(tier):
            if a["name"] not in seen:
                seen.add(a["name"])
                out.append(a)
    return out


def render_action_centre(base=Path(".")):
    import streamlit as st

    st.subheader("Action Centre: suggested responses by station")
    st.warning("Advisory only. These are prompts for a municipal officer to review. They are not orders, "
               "not an official CPCB warning, and not confirmation of any pollution source.", icon=":material/info:")

    data = load_latest(base)
    if data["dir"] is None:
        for p in data["problems"]:
            st.error(p)
        st.info(f"No 4-station outputs found. Run `{RUN_HINT}` from the repository root, then reload.")
        return
    lf, hist, metrics = data["latest"], data["history"], data["metrics"]
    if lf.empty:
        st.warning("latest_forecast.csv is empty.")
        return
    for p in data["problems"]:
        st.warning(p)

    age = snapshot_age_days(lf)
    st.caption(f"Stored snapshot (not live). Latest usable day: {_fmt_date(lf['as_of_date'].max())}.")
    if age is not None and age > STALE_DAYS:
        st.warning(f"This snapshot is {age} days old. Treat every estimate below as stale.")

    ranked = lf.sort_values(["estimate_pm25", "high_80"], ascending=False).reset_index(drop=True)
    name = st.selectbox("Station (highest estimate first)", list(ranked["station_short"]), key="ac_station")
    row = ranked[ranked["station_short"] == name].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Estimate for {_fmt_date(row['forecast_for_date'])}", f"{row['estimate_pm25']:.0f} ug/m3")
    c2.metric("80% empirical range", f"{row['low_80']:.0f} to {row['high_80']:.0f}")
    c3.markdown("Heuristic tier")
    c3.markdown(f":{TIER_COLOR.get(row['tier_heuristic'], 'gray')}[**{row['tier_heuristic']}**]"
                + (f"  \nUpper bound reaches **{row['tier_at_upper_bound']}**"
                   if row["tier_at_upper_bound"] != row["tier_heuristic"] else ""))

    st.markdown("##### Suggested response (for review)")
    st.markdown(row["suggested_action"])

    st.markdown("##### Data-quality warnings")
    health = data_health(lf, hist)
    warns = []
    if not health.empty:
        hr = health[health["station"] == row["station"]].iloc[0]
        warns += station_warnings(hr)
    cov = coverage_for_level(metrics, float(row["estimate_pm25"]))
    if cov and cov[1].get("coverage") is not None and cov[1]["coverage"] < 0.70:
        warns.append(f"At this PM2.5 level {cov[0]}, measured band coverage was only "
                     f"{cov[1]['coverage']:.0%} on {cov[1]['n']} past days. The range is less reliable here.")
    if warns:
        for w in warns:
            st.warning(w)
    else:
        st.success("No data-quality warnings were triggered for this station by the checks in this tool. "
                   "This does not prove the sensor is working correctly.")

    actions = _actions_for(row)
    st.markdown("##### Related library actions and responsible roles (illustrative)")
    st.caption("Confirm roles against your own procedures. Entries cover both the estimate tier and the "
               "upper-bound tier.")
    for a in actions:
        with st.expander(a["name"]):
            st.markdown(f"**Trigger:** {a['trigger']}")
            st.markdown(f"**Suggested response:** {a['response']}")
            st.markdown(f"**Responsible stakeholder (illustrative):** {a['stakeholder']}")
            st.markdown(f"**Limitations:** {a['limits']}")
    roles = sorted({a["stakeholder"] for a in actions})
    if roles:
        st.markdown("**Roles involved:** " + "; ".join(roles))

    with st.expander("Relevant limitations"):
        for item in LIMITATIONS:
            st.markdown(f"- {item}")
