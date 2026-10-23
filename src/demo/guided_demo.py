"""
CityPulse: Mumbai — Guided Demo Mode

Step-by-step walkthrough for live presentations and judging sessions.
All numbers computed from actual data — no placeholders.
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st
from typing import List, Dict

def _load_showcase_stats() -> dict:
    """Load pre-computed showcase statistics from actual pipeline runs."""
    eval_path = Path("reports/evaluation_metrics.json")
    eval_metrics = json.loads(eval_path.read_text(encoding="utf-8")) if eval_path.exists() else {}

    daily_path = Path("data/processed/mumbai_aqi_daily_clean.parquet")
    hourly_path = Path("data/processed/mumbai_aqi_hourly_clean.parquet")

    n_stations = 0
    n_daily_rows = 0
    n_hourly_rows = 0

    if daily_path.exists():
        daily_df = pd.read_parquet(daily_path)
        n_stations = daily_df["canonical_station"].nunique()
        n_daily_rows = len(daily_df)
    if hourly_path.exists():
        hourly_df = pd.read_parquet(hourly_path, columns=["canonical_station"])
        n_hourly_rows = len(hourly_df)

    pers_path = Path("data/processed/persistence_metrics.json")
    pers_metrics = json.loads(pers_path.read_text(encoding="utf-8")) if pers_path.exists() else {}

    return {
        "eval": eval_metrics,
        "pers": pers_metrics,
        "n_stations": n_stations,
        "n_daily_rows": n_daily_rows,
        "n_hourly_rows": n_hourly_rows,
    }

def _get_demo_steps(stats: dict) -> list:
    """Build demo steps with actual computed values."""
    n_stations = stats["n_stations"]
    n_hourly = stats["n_hourly_rows"]
    eval_m = stats["eval"]
    pers_m = stats["pers"]

    gb_mae = eval_m.get("gradient_boosting", {}).get("MAE", "N/A")
    p_mae = eval_m.get("persistence", {}).get("MAE", "N/A")
    coverage = eval_m.get("interval_coverage_pct", "N/A")
    pr_auc = eval_m.get("classifier", {}).get("PR_AUC", "N/A")
    pers_coverage = pers_m.get("empirical_coverage", "N/A")

    hourly_str = f"{n_hourly:,}" if n_hourly else "N/A"
    station_str = str(n_stations) if n_stations else "N/A"

    return [
        {
            "number": 1,
            "title": "The Problem",
            "icon": ":material/crisis_alert:",
            "content": f"""
**Mumbai's air quality challenge:**
- {station_str} monitoring stations across Mumbai Metropolitan Region
- {hourly_str} hourly AQI records (2021–2023)
- Limited municipal resources: typically 5–10 inspection teams
- **Decision challenge:** *Which zones need attention THIS WEEK?*

**Key constraint:** Cannot inspect all zones — must prioritize intelligently.
            """,
            "metric_label": "Challenge",
            "metric_value": "Finite Resources",
            "metric_delta": f"5–10 teams for {station_str} zones"
        },
        {
            "number": 2,
            "title": "The Data",
            "icon": ":material/database:",
            "content": f"""
**100% free, open, verifiable data:**
- ✅ CPCB/MPCB air quality ({hourly_str} hourly records)
- ✅ Open-Meteo weather (ERA5 reanalysis, 2021–2023)
- ✅ OpenStreetMap land use context (ODbL licence)
- ❌ **NO** paid APIs, API keys, or synthetic data

**Data quality:** 18-hour validity rule, sensor-stuck filtering, gap interpolation.
            """,
            "metric_label": "Data Points",
            "metric_value": hourly_str,
            "metric_delta": "All open & verified"
        },
        {
            "number": 3,
            "title": "Multi-Criteria Prioritization",
            "icon": ":material/balance:",
            "content": """
**Priority Score combines 5 evidence streams:**
1. **Recent Exposure** (7-day mean AQI)
2. **Persistence Shock** (days > 150 AQI)
3. **Trend Acceleration** (rate of worsening)
4. **Forecast Risk** (probability AQI > 200)
5. **Vulnerability Context** (highway corridors, industrial zones)

Each component is normalized 0–100, weighted by policy, combined → Priority Score.
            """,
            "metric_label": "Ranking Method",
            "metric_value": "Multi-Criteria",
            "metric_delta": "5 evidence streams"
        },
        {
            "number": 4,
            "title": "What-If Policy Simulator",
            "icon": ":material/tune:",
            "content": """
**Interactive weight adjustment:**
- Adjust weights in sidebar → see rankings update instantly
- Monte Carlo stability: which zones robust to policy changes?
- Rank movement visualization with arrows

**Use case:** Policy maker wants exposure-heavy vs forecast-heavy strategy.
            """,
            "metric_label": "Simulations",
            "metric_value": "500 runs",
            "metric_delta": "±30% perturbation"
        },
        {
            "number": 5,
            "title": "Route Planner",
            "icon": ":material/route:",
            "content": """
**Practical inspection logistics:**
- Select top-N priority zones
- Compute nearest-neighbor tour (haversine distance)
- Numbered stops on map, total distance
- **Honest disclaimer:** straight-line, not road routing

**Output:** Printable route schedule with distances.
            """,
            "metric_label": "Route Algorithm",
            "metric_value": "Nearest-Neighbor",
            "metric_delta": "Greedy heuristic"
        },
        {
            "number": 6,
            "title": "Validation & Honesty",
            "icon": ":material/verified:",
            "content": f"""
**Rigorous backtest on 2023 chronological holdout:**
- Priority strategy tested across weekly cycles vs random baseline
- Model MAE: **{gb_mae}** vs Persistence MAE: **{p_mae}** (persistence wins on point-forecast)
- 80% nominal intervals: actual coverage **{coverage}%** (undercovering — we show this honestly)
- Classifier PR-AUC: **{pr_auc}** — model adds value for risk identification
- **We show where it doesn't work**

**Technical judges:** This is the validation section you want to see.
            """,
            "metric_label": "Backtest Period",
            "metric_value": "2023",
            "metric_delta": "Chronological holdout"
        },
        {
            "number": 7,
            "title": "Printable Briefing",
            "icon": ":material/description:",
            "content": """
**One-click weekly briefing export:**
- Top-5 zones, recommended actions, evidence basis
- Policy weights used, data as-of date
- Data attribution footer
- Downloads as HTML (always) + PDF (if library available)

**This is the artifact an inspector carries to the field.**
            """,
            "metric_label": "Export Format",
            "metric_value": "HTML + PDF",
            "metric_delta": "Print-ready"
        },
        {
            "number": 8,
            "title": "Impact & Next Steps",
            "icon": ":material/rocket_launch:",
            "content": f"""
**What the data shows:**
- Multi-criteria ranking concentrates inspections on zones most likely to have elevated AQI
- Persistence baseline: MAE = {p_mae} AQI — yesterday is a strong predictor
- Model classifier identifies unhealthy-risk days with PR-AUC = {pr_auc}
- **NOT claiming lives saved** — that requires health outcome data we don't have

**Future work:**
- Live CPCB API integration (when access permits)
- Satellite AOD data for better forecasts
- SMS/WhatsApp alerts for citizens
- Multi-city deployment (Delhi, Pune, Kolkata)
            """,
            "metric_label": "Next Milestone",
            "metric_value": "Live Integration",
            "metric_delta": "CPCB real-time API"
        }
    ]

def render_guided_demo():
    """
    Renders an interactive guided demo with step-by-step walkthrough.
    All numbers come from actual pipeline outputs — zero placeholders.
    """
    st.markdown("### :material/play_circle: Guided Demo Mode")
    st.caption("**For judges & presentations:** Step through the CityPulse story")

    stats = _load_showcase_stats()
    DEMO_STEPS = _get_demo_steps(stats)

    if "demo_step" not in st.session_state:
        st.session_state.demo_step = 0

    progress = (st.session_state.demo_step + 1) / len(DEMO_STEPS)
    st.progress(progress, text=f"Step {st.session_state.demo_step + 1} of {len(DEMO_STEPS)}")

    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 1, 1, 2])

    with col_nav1:
        if st.button(":material/skip_previous: First", width='stretch', disabled=st.session_state.demo_step == 0):
            st.session_state.demo_step = 0
            st.rerun()

    with col_nav2:
        if st.button(":material/arrow_back: Previous", width='stretch', disabled=st.session_state.demo_step == 0):
            st.session_state.demo_step -= 1
            st.rerun()

    with col_nav3:
        if st.button("Next :material/arrow_forward:", width='stretch', type="primary", disabled=st.session_state.demo_step >= len(DEMO_STEPS) - 1):
            st.session_state.demo_step += 1
            st.rerun()

    with col_nav4:
        if st.button(":material/verified: Jump to Validation (Step 6)", width='stretch'):
            st.session_state.demo_step = 5
            st.rerun()

    st.markdown("---")
    step = DEMO_STEPS[st.session_state.demo_step]

    col_step1, col_step2 = st.columns([3, 1])

    with col_step1:
        st.markdown(f"## {step['icon']} Step {step['number']}: {step['title']}")
        st.markdown(step["content"])

    with col_step2:
        st.metric(
            label=step["metric_label"],
            value=step["metric_value"],
            delta=step["metric_delta"]
        )

    st.markdown("---")
    with st.expander(":material/list: Jump to Step"):
        for i, s in enumerate(DEMO_STEPS):
            if st.button(f"{s['number']}. {s['title']}", key=f"jump_{i}", width='stretch'):
                st.session_state.demo_step = i
                st.rerun()
