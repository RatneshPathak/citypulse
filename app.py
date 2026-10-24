"""
CityPulse: Mumbai — Urban Intelligence & Environmental Decision Command Center
Predict • Explain • Act

Municipal Decision Support System (BMC / MPCB).
Professional command-center architecture, high-contrast dark theme (#0B1220 / #162235 / #2DD4BF),
structured grouped navigation, transparent historical replay status, and honest data disclosures.
"""
import json
import importlib
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import components as ui_components
ui_components = importlib.reload(ui_components)
from components import (
    render_action_dossier,
    render_action_strip,
    render_compact_banner,
    render_data_status_bar,
    render_footer,
    render_header,
    render_kpi_card,
    render_ranked_summary,
    render_source_card,
    render_takeaway,
)
from icons import ICONS
from config import EVENT_NAME, TEAM_MEMBERS, DATA_ATTRIBUTION
import theme
theme = importlib.reload(theme)
from theme import AQI_PALETTE, COLORS, get_aqi_category_color, get_priority_tier
import charts
charts = importlib.reload(charts)

from src.decision.whatif import compute_rank_stability, compute_rank_delta
from src.decision.routing import compute_inspection_route
from src.decision.briefing import render_briefing_export_ui
from src.decision.validation import render_validation_panel
from src.decision.reliability import station_reliability
from src.decision import viz as decision_viz
decision_viz = importlib.reload(decision_viz)

from src.citizen.citizen_view import render_citizen_mode, render_aqi_card_export
from src.demo.guided_demo import render_guided_demo
from src.demo.replay_dates import shift_date_columns

# Page Configuration
st.set_page_config(
    page_title="CityPulse: Mumbai — Urban Intelligence Command Center",
    page_icon=ICONS["page_icon"],
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.inject_custom_css()

# Data Paths
DATA_PATH = Path("data/processed/mumbai_aqi_daily_clean.parquet")
PREDICTIONS_PATH = Path("data/processed/holdout_predictions.parquet")
PRIORITY_PATH = Path("data/processed/mumbai_priority_rankings.parquet")
METRICS_PATH = Path("reports/evaluation_metrics.json")

@st.cache_data
def load_all_datasets():
    daily = pd.read_parquet(DATA_PATH) if DATA_PATH.exists() else pd.DataFrame()
    preds = pd.read_parquet(PREDICTIONS_PATH) if PREDICTIONS_PATH.exists() else pd.DataFrame()
    priority = pd.read_parquet(PRIORITY_PATH) if PRIORITY_PATH.exists() else pd.DataFrame()

    if not daily.empty:
        delta = pd.Timestamp.now().normalize() - pd.to_datetime(daily["date"], errors="raise").max()
        shift_date_columns(daily, ("date",), delta)
        if not preds.empty:
            shift_date_columns(preds, ("date",), delta)
        if not priority.empty:
            shift_date_columns(priority, ("date", "target_date"), delta)

    return daily, preds, priority

def _get_data_freshness():
    """Returns data freshness metadata from actual file timestamps and data ranges."""
    info = {}
    if DATA_PATH.exists():
        mtime = datetime.fromtimestamp(DATA_PATH.stat().st_mtime)
        info["file_updated"] = mtime.strftime("%d %b %Y, %H:%M IST")
    if PREDICTIONS_PATH.exists():
        mtime = datetime.fromtimestamp(PREDICTIONS_PATH.stat().st_mtime)
        info["model_updated"] = mtime.strftime("%d %b %Y, %H:%M IST")
    return info

daily_df, preds_df, priority_df = load_all_datasets()
data_freshness = _get_data_freshness()

if daily_df.empty or preds_df.empty:
    st.error("Processed datasets missing. Run `python -m src.clean.clean_pipeline` first.", icon=":material/error:")
    st.stop()

# Default Policy Weights
DEFAULT_WEIGHTS = {
    "w_exp": 0.30,
    "w_pers": 0.25,
    "w_trend": 0.15,
    "w_fore": 0.20,
    "w_gap": 0.10,
}

if "weights" not in st.session_state:
    st.session_state.weights = DEFAULT_WEIGHTS.copy()

# Station Discovery
target_day = preds_df["date"].max()
recent_predictions = preds_df[(preds_df["date"] < target_day) & (preds_df["date"] >= target_day - pd.Timedelta(days=7))]
all_stations = sorted(
    set(daily_df["canonical_station"].dropna())
    & set(preds_df.loc[preds_df["date"] == target_day, "canonical_station"].dropna())
    & set(recent_predictions["canonical_station"].dropna())
)

default_station = "Bandra Kurla Complex" if "Bandra Kurla Complex" in all_stations else all_stations[0]
if "selected_station" not in st.session_state or st.session_state.selected_station not in all_stations:
    st.session_state.selected_station = default_station

# Dynamic Priority Scoring
@st.cache_data
def get_cached_priority_scores(w_dict):
    from src.models.prioritization import compute_station_priority_scores
    return compute_station_priority_scores(
        preds_df,
        w_exposure=w_dict["w_exp"],
        w_persistence=w_dict["w_pers"],
        w_trend=w_dict["w_trend"],
        w_forecast=w_dict["w_fore"],
        w_gap=w_dict["w_gap"],
    )

dyn_priority = get_cached_priority_scores(st.session_state.weights)
decision_date = pd.to_datetime(dyn_priority["date"].iloc[0]).strftime("%d %b %Y")
target_date = pd.to_datetime(dyn_priority["target_date"].iloc[0]).strftime("%d %b %Y")
data_start = daily_df["date"].min().strftime("%d %b %Y")
data_end = daily_df["date"].max().strftime("%d %b %Y")

reliability_df = station_reliability(daily_df, dyn_priority["date"].iloc[0])

# ==========================================
# SIDEBAR NAVIGATION (5 PRIMARY SECTIONS)
# ==========================================
st.sidebar.markdown(
    f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">'
    f'  <div style="width:36px; height:36px; background:rgba(45,212,191,0.15); border:1px solid #2DD4BF; border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0;">'
    f'    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><path d="M3 21h18M5 21V7l8-4v18M13 21V11l6 3v7M8 10h1M8 14h1M8 18h1M16 16h1M16 19h1"/></svg>'
    f'  </div>'
    f'  <div>'
    f'    <div style="font-size:1.05rem; font-weight:800; color:#ffffff; line-height:1.2;">CityPulse</div>'
    f'    <div style="font-size:0.68rem; font-weight:700; color:#2DD4BF; letter-spacing:0.08em; text-transform:uppercase;">Mumbai Urban Intelligence</div>'
    f'  </div>'
    f'</div>',
    unsafe_allow_html=True,
)

st.sidebar.caption("BMC / MPCB Environmental Command Console")

NAV_SECTIONS = [
    ":material/dashboard: Overview",
    ":material/crisis_alert: Decision Center",
    ":material/insights: Air Quality Insights",
    ":material/psychology: Model Intelligence",
    ":material/folder_open: Citizen & Reports",
]

# Sync navigation state
if "nav_section_idx" not in st.session_state:
    st.session_state.nav_section_idx = 0

def on_nav_change():
    chosen = st.session_state.nav_radio
    st.session_state.nav_section_idx = NAV_SECTIONS.index(chosen)

selected_nav_label = st.sidebar.radio(
    "Navigation Console",
    NAV_SECTIONS,
    index=st.session_state.nav_section_idx,
    key="nav_radio",
    on_change=on_nav_change,
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

# Location Target in Sidebar
st.sidebar.markdown(f"##### {ICONS['sidebar_location']} Monitored Station Focus")
focus_idx = all_stations.index(st.session_state.selected_station) if st.session_state.selected_station in all_stations else 0
chosen_station = st.sidebar.selectbox(
    "Focus Station / Ward",
    all_stations,
    index=focus_idx,
    help="Continuous monitoring station for micro-climate analysis and action protocols.",
    label_visibility="collapsed",
)
if chosen_station != st.session_state.selected_station:
    st.session_state.selected_station = chosen_station

selected_station = st.session_state.selected_station

# Resource Budget
st.sidebar.markdown(f"##### {ICONS['sidebar_budget']} Municipal Resource Capacity")
capacity_n = st.sidebar.slider(
    "Inspection Fleet Capacity (Top Zones)",
    1, 15, 5,
    help="Number of priority zones the municipal enforcement fleet has resources to physically inspect this week.",
)

# Policy Weights in Sidebar (Expandable / Clean)
with st.sidebar.expander(f"{ICONS['sidebar_weights']} Prioritisation Policy Weights", expanded=False):
    st.caption("Adjust weight of multi-criteria evidence:")
    
    if st.button("Reset Weights", icon=ICONS["sidebar_reset"], width='stretch'):
        st.session_state.weights = DEFAULT_WEIGHTS.copy()
        st.rerun()

    w_exp = st.slider("Recent Exposure (7-day)", 0.0, 1.0, float(st.session_state.weights["w_exp"]), 0.05)
    w_pers = st.slider("Persistence Shock (>150)", 0.0, 1.0, float(st.session_state.weights["w_pers"]), 0.05)
    w_trend = st.slider("Trend Acceleration", 0.0, 1.0, float(st.session_state.weights["w_trend"]), 0.05)
    w_fore = st.slider("Forecast Risk (24h)", 0.0, 1.0, float(st.session_state.weights["w_fore"]), 0.05)
    w_gap = st.slider("Vulnerability Corridor", 0.0, 1.0, float(st.session_state.weights["w_gap"]), 0.05)

    st.session_state.weights = {
        "w_exp": w_exp,
        "w_pers": w_pers,
        "w_trend": w_trend,
        "w_fore": w_fore,
        "w_gap": w_gap,
    }
    total_w = sum(st.session_state.weights.values())
    if abs(total_w - 1.0) < 0.01:
        st.success(f"Weights Balanced ({total_w:.2f})", icon=":material/check_circle:")
    else:
        st.caption(f"Normalized Total: {total_w:.2f} (auto-scaled to 100%)")

st.sidebar.markdown("---")
st.sidebar.markdown(
    f'<div style="background: rgba(22, 34, 53, 0.7); border: 1px solid {COLORS["border"]}; border-radius: 8px; padding: 10px 12px; font-size: 0.74rem;">'
    f'  <div style="font-weight: 700; color: #ffffff; margin-bottom: 4px;">Historical Decision Replay</div>'
    f'  <div style="color: {COLORS["text_muted"]}; line-height: 1.4;">'
    f'    Replay Date: <strong style="color: #ffffff;">{decision_date}</strong><br>'
    f'    Screening Target: <strong style="color: #ffffff;">{target_date}</strong><br>'
    f'    Source: <span style="color: #2DD4BF;">CPCB CAAQMS & ERA5</span>'
    f'  </div>'
    f'</div>',
    unsafe_allow_html=True,
)

with st.sidebar.expander(f"{ICONS['info']} About CityPulse", expanded=False):
    st.markdown(f"**Built for {EVENT_NAME}**  \nby **{TEAM_MEMBERS}**")
    st.caption(
        "CityPulse: Mumbai is an air quality prioritisation and decision-support prototype "
        "for municipal environmental planning and inspection triage (BMC / MPCB role). "
        "Not an official warning system.\n\n"
        f"**Data Sources:** {DATA_ATTRIBUTION}."
    )

# Prepare Active Station Slice
st_daily = daily_df[
    (daily_df["canonical_station"] == selected_station)
    & (daily_df["date"] <= pd.to_datetime(dyn_priority["date"].iloc[0]))
].sort_values("date").copy()
st_preds = preds_df[preds_df["canonical_station"] == selected_station].sort_values("date").copy()
st_prio_row = dyn_priority[dyn_priority["station"] == selected_station]
st_prio = st_prio_row.iloc[0]

station_reliability_row = reliability_df.loc[reliability_df["station"] == selected_station]
confidence_label = "Medium"
if not station_reliability_row.empty:
    confidence_label = station_reliability_row.iloc[0]["confidence"]

# Persistent Command Center Header
render_header(selected_station, decision_date, total_stations=daily_df["canonical_station"].nunique())

# Transparent Data-Status Bar
render_data_status_bar(
    decision_date=decision_date,
    target_date=target_date,
    reliability_label=confidence_label,
    total_stations=daily_df["canonical_station"].nunique(),
    observation_range=f"{data_start} – {data_end}",
    data_source="CPCB / MPCB & Open-Meteo ERA5",
)

render_compact_banner()

# ==============================================================================
# SECTION 1: OVERVIEW (THE GRAND COMMAND CENTER OPENING VIEW)
# ==============================================================================
if "Overview" in selected_nav_label:
    render_takeaway(
        f"In the {decision_date} decision replay, <strong>{dyn_priority.iloc[0]['station']}</strong> ranks #1 "
        f"(Priority Score: {dyn_priority.iloc[0]['priority_score']:.1f}/100, Observed AQI: {dyn_priority.iloc[0]['latest_aqi']:.0f}). "
        f"The top {capacity_n} priority zones form the immediate municipal field inspection schedule."
    )

    # 4 Command Center KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card(
            "Priority Zones",
            f"{capacity_n:02d}",
            "Selected for immediate field inspection",
            color_accent="#EF4444",
            badge="ACTION QUEUE",
        )
    with k2:
        render_kpi_card(
            "Monitoring Stations",
            f"{daily_df['canonical_station'].nunique():02d}",
            "Quality-filtered continuous CPCB stations",
            color_accent="#2DD4BF",
            badge="ACTIVE NETWORK",
        )
    with k3:
        render_kpi_card(
            "Planning Horizon",
            "7 Days",
            "Weekly prioritization & resource triage",
            color_accent="#38BDF8",
            badge="CYCLE",
        )
    with k4:
        render_kpi_card(
            "Risk Forecast",
            "Next Day",
            f"Holdout screening targeting {target_date}",
            color_accent="#F59E0B",
            badge="MODEL RISK",
        )

    st.markdown("---")

    # Inspection Priority Map Header & Filters
    col_map_hdr, col_map_fltr = st.columns([1.5, 1])
    with col_map_hdr:
        st.markdown(f"### {ICONS['map']} Inspection Priority Map")
        st.caption("Click any monitoring station on the map or select from the dropdown to inspect its micro-evidence.")
    with col_map_fltr:
        priority_filter = st.segmented_control(
            "Filter Priority Tier",
            options=["All", "Highest Priority", "Elevated Priority", "Routine"],
            default="All",
            label_visibility="collapsed",
        )

    # Main Visual Element: Large Geospatial Map
    fig_map = charts.plot_priority_map(
        dyn_priority,
        selected_station=selected_station,
        priority_filter=priority_filter if priority_filter else "All",
        capacity_n=capacity_n,
    )

    map_selection = st.plotly_chart(
        fig_map,
        width='stretch',
        config=charts.CHART_CONFIG,
        on_select="rerun",
        selection_mode="points",
        key="overview_priority_map",
    )

    # Interactive map click integration
    if map_selection and "points" in map_selection and map_selection["points"]:
        pt = map_selection["points"][0]
        if "customdata" in pt and pt["customdata"]:
            clicked_station = pt["customdata"][0]
            if clicked_station in all_stations and clicked_station != st.session_state.selected_station:
                st.session_state.selected_station = clicked_station
                st.rerun()

    st.caption("Map tiles: © OpenStreetMap contributors, © CARTO. Dot color: Inspection Priority Tier • Dot size: Observed AQI.")

    st.markdown("---")

    # Two-Column Command Layout: Station Details Panel + Top Ranked Summary
    col_details, col_ranked = st.columns([1.2, 1.1], gap="large")

    with col_details:
        st.markdown(f"### :material/badge: Station Dossier: **{selected_station}**")
        
        sel_cat_name, sel_cat_col = get_aqi_category_color(st_prio["latest_aqi"])
        tier_label, tier_col = get_priority_tier(st_prio["rank"], capacity_n=capacity_n)

        d1, d2, d3 = st.columns(3)
        with d1:
            render_kpi_card(
                "Inspection Rank",
                f"#{st_prio['rank']}",
                tier_label,
                color_accent=tier_col,
            )
        with d2:
            render_kpi_card(
                "Priority Score",
                f"{st_prio['priority_score']:.1f}",
                "Scale 0 – 100",
                color_accent=COLORS["accent"],
            )
        with d3:
            render_kpi_card(
                "Observed AQI",
                f"{st_prio['latest_aqi']:.0f}",
                f"CPCB: {sel_cat_name}",
                color_accent=sel_cat_col,
            )

        # Contributing factor breakdown
        st.markdown("##### Score Contribution Breakdown")
        fig_breakdown = charts.plot_score_breakdown(st_prio.to_dict(), st.session_state.weights)
        st.plotly_chart(fig_breakdown, width='stretch', config=charts.CHART_CONFIG)

        # Data reliability callout
        if not station_reliability_row.empty:
            rel = station_reliability_row.iloc[0]
            st.markdown(
                f'<div style="background:{COLORS["surface"]}; border:1px solid {COLORS["border"]}; border-radius:8px; padding:10px 14px; font-size:0.80rem; margin-top:8px;">'
                f'  <strong>Data Coverage Quality:</strong> {rel["coverage_pct"]:.1f}% usable hours in past 30 days '
                f'  (<span style="color: #2DD4BF;">{rel["valid_days"]} valid days</span> • Confidence: <strong>{rel["confidence"]}</strong>)'
                f'</div>',
                unsafe_allow_html=True,
            )

        render_action_dossier(st_prio.to_dict(), allocated=(st_prio["rank"] <= capacity_n))

    with col_ranked:
        render_ranked_summary(dyn_priority, top_n=min(5, capacity_n))

        st.markdown("---")
        st.markdown("##### Next Operational Steps")
        st.markdown(
            "1. **Audit priority rankings** across the entire 30-station metropolitan network.\n"
            "2. **Simulate what-if weight scenarios** for industrial vs vehicular focus.\n"
            "3. **Compute the optimal inspection route** for field teams."
        )

        if st.button("🚀 Open Full Decision Center & Policy Simulator →", type="primary", width='stretch'):
            st.session_state.nav_section_idx = 1
            st.rerun()

# ==============================================================================
# SECTION 2: DECISION CENTER
# ==============================================================================
elif "Decision Center" in selected_nav_label:
    render_takeaway(
        "Evaluate multi-criteria priority rankings, test weight sensitivities in the What-If Simulator, "
        "generate inspection route tours, and export weekly municipal briefings."
    )

    dec_tab1, dec_tab2, dec_tab3, dec_tab4 = st.tabs([
        f"{ICONS['tab_act']} Priority Rankings",
        f":material/tune: What-If Policy Simulator",
        f":material/route: Inspection Route Planner",
        f":material/description: Executive Briefing Export",
    ])

    # 1. PRIORITY RANKINGS
    with dec_tab1:
        st.markdown(f"### {ICONS['leaderboard']} Complete Priority Rankings & Action Roster")
        st.caption("Sortable multi-criteria rankings combining 7-day exposure, persistence shock, trend acceleration, forecast risk, and vulnerability corridors.")

        render_action_strip(dyn_priority, top_n=min(5, capacity_n))

        st.markdown("---")

        table_df = dyn_priority.copy()
        table_df["Action"] = np.where(table_df["rank"] <= capacity_n, "INSPECT", "ROUTINE")
        table_df["Category"] = table_df["latest_aqi"].apply(lambda v: get_aqi_category_color(v)[0])

        table_df = table_df.merge(
            reliability_df[["station", "coverage_pct", "missing_hours_pct", "confidence"]],
            on="station", how="left"
        )
        table_df["coverage_pct"] = table_df["coverage_pct"].fillna(0)
        table_df["missing_hours_pct"] = table_df["missing_hours_pct"].fillna(100)
        table_df["confidence"] = table_df["confidence"].fillna("Low")

        display_df = table_df[[
            "rank", "station", "priority_score", "latest_aqi", "Category", "coverage_pct", "missing_hours_pct", "confidence", "Action", "zone"
        ]].rename(columns={
            "rank": "Rank",
            "station": "Zone / Station",
            "priority_score": "Score",
            "latest_aqi": "AQI",
            "coverage_pct": "Coverage %",
            "missing_hours_pct": "Unavailable %",
            "confidence": "Confidence",
            "Action": "Action Status",
            "zone": "Zone",
        })

        st.dataframe(
            display_df,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", width="small", format="#%d"),
                "Score": st.column_config.ProgressColumn(
                    "Priority Score",
                    help="Composite score combining recent exposure, persistence, trend, and forecast.",
                    format="%.1f",
                    min_value=0,
                    max_value=100,
                    width="medium",
                ),
                "AQI": st.column_config.NumberColumn("Latest AQI", format="%.0f", width="small"),
                "Category": st.column_config.TextColumn("CPCB Category", width="small"),
                "Coverage %": st.column_config.ProgressColumn("Usable Hours", format="%.0f%%", min_value=0, max_value=100, width="small"),
                "Unavailable %": st.column_config.NumberColumn("Unavailable %", format="%.1f%%", width="small"),
                "Confidence": st.column_config.TextColumn("Data Confidence", width="small"),
                "Action Status": st.column_config.TextColumn("Action Status", width="small"),
                "Zone": st.column_config.TextColumn("Region", width="medium"),
            },
            hide_index=True,
            width='stretch',
            height=380,
        )

        st.markdown("---")
        st.markdown(f"##### {ICONS['analytics']} Deep-Dive Evidence: **{selected_station}**")
        fig_bd = charts.plot_score_breakdown(st_prio.to_dict(), st.session_state.weights)
        st.plotly_chart(fig_bd, width='stretch', config=charts.CHART_CONFIG)

        render_action_dossier(st_prio.to_dict(), allocated=(st_prio["rank"] <= capacity_n))

    # 2. WHAT-IF POLICY SIMULATOR
    with dec_tab2:
        st.markdown("### :material/tune: Policy Weight What-If Simulator")
        st.caption(
            "Simulate how shifting municipal priorities changes zone triage. "
            "Compare adjusted rankings side-by-side against baseline defaults and verify robustness via Monte Carlo simulation."
        )

        if "baseline_priority" not in st.session_state:
            st.session_state.baseline_priority = dyn_priority.copy()

        c_base1, c_base2 = st.columns(2)
        with c_base1:
            if st.button("📌 Set Current as Comparison Baseline", width='stretch'):
                st.session_state.baseline_priority = dyn_priority.copy()
                st.success("New baseline locked!", icon=":material/check_circle:")
        with c_base2:
            if st.button("🔄 Reset to Default Policy Weights", width='stretch'):
                st.session_state.weights = DEFAULT_WEIGHTS.copy()
                st.rerun()

        st.markdown("---")
        st.markdown("#### Rank Movement Analysis")

        delta_df = compute_rank_delta(st.session_state.baseline_priority, dyn_priority)
        big_movers = delta_df[delta_df["delta"].abs() >= 2].head(10)

        col_move1, col_move2 = st.columns(2)
        with col_move1:
            st.markdown("**Notable Rank Adjustments:**")
            if not big_movers.empty:
                for _, row in big_movers.head(5).iterrows():
                    direction_icon = "📈" if row["delta"] > 0 else "📉"
                    st.markdown(f"{direction_icon} **{row['station']}**: #{row['old_rank']} → #{row['new_rank']} ({row['movement']})")
            else:
                st.info("No significant rank changes with current weights.", icon=":material/info:")

        with col_move2:
            moved_up = (delta_df["delta"] > 0).sum()
            moved_down = (delta_df["delta"] < 0).sum()
            unchanged = (delta_df["delta"] == 0).sum()
            st.markdown("**Ranking Net Mobility:**")
            st.markdown(f"- 📈 Priority elevated: **{moved_up}** zones")
            st.markdown(f"- 📉 Priority lowered: **{moved_down}** zones")
            st.markdown(f"- ➖ Rank unchanged: **{unchanged}** zones")

        if len(dyn_priority) > 0:
            fig_movement = decision_viz.plot_rank_movement(
                st.session_state.baseline_priority,
                dyn_priority,
                top_n=15
            )
            st.plotly_chart(fig_movement, width='stretch', config=charts.CHART_CONFIG)

        # Collapsible Monte Carlo Stability Analysis
        with st.expander("🎲 Monte Carlo Rank Stability Analysis (500 Iterations)", expanded=False):
            st.caption(
                "Evaluates zones that are **robust** to policy choices vs those that are **sensitive** by running 500 simulations with ±30% weight perturbations."
            )
            run_stability = st.button("▶️ Run Monte Carlo Simulation", help="Simulates 500 randomized weight variations")

            if run_stability or "stability_results" in st.session_state:
                if run_stability:
                    with st.spinner("Executing 500 Monte Carlo iterations..."):
                        stability_df = compute_rank_stability(
                            preds_df,
                            baseline_weights=st.session_state.weights,
                            n_simulations=500,
                            perturbation_pct=0.30,
                            target_n=capacity_n
                        )
                        st.session_state.stability_results = stability_df

                stability_df = st.session_state.stability_results

                col_stab1, col_stab2 = st.columns(2)
                with col_stab1:
                    fig_prob = decision_viz.plot_probability_heatmap(stability_df, top_n=capacity_n)
                    st.plotly_chart(fig_prob, width='stretch', config=charts.CHART_CONFIG)
                with col_stab2:
                    fig_ranges = decision_viz.plot_rank_stability_ranges(stability_df, top_n=10)
                    st.plotly_chart(fig_ranges, width='stretch', config=charts.CHART_CONFIG)

                robust_zones = stability_df[stability_df["prob_top_n"] > 0.80].head(5)
                unstable_zones = stability_df[stability_df["rank_range"] > 10].head(5)

                col_interp1, col_interp2 = st.columns(2)
                with col_interp1:
                    st.markdown(f"**✅ Robust Top-{capacity_n} Zones (>80% probability):**")
                    for _, rz in robust_zones.iterrows():
                        st.markdown(f"- **{rz['station']}**: {rz['prob_top_n']*100:.0f}% chance in top-{capacity_n}")
                with col_interp2:
                    st.markdown("**⚠️ Rank-Sensitive Zones (wide variance):**")
                    for _, uz in unstable_zones.iterrows():
                        st.markdown(f"- **{uz['station']}**: ranks #{uz['rank_min']} to #{uz['rank_max']} (span: {uz['rank_range']})")

    # 3. ROUTE PLANNER
    with dec_tab3:
        st.markdown("### :material/route: Inspection Route Planner")
        st.caption(f"Calculates an efficient inspection tour across the top {capacity_n} priority zones using nearest-neighbor spatial routing.")

        selected_route_stations = dyn_priority.head(capacity_n)
        route_lat = pd.to_numeric(selected_route_stations["latitude"], errors="coerce")
        route_lon = pd.to_numeric(selected_route_stations["longitude"], errors="coerce")
        route_mask = route_lat.between(-90, 90) & route_lon.between(-180, 180)
        route_locations = selected_route_stations.loc[route_mask].copy()
        top_stations_list = route_locations["station"].tolist()

        r_c1, r_c2 = st.columns([2, 1])
        with r_c1:
            start_station_route = st.selectbox(
                "Starting Depot / Municipal HQ",
                ["Highest Priority Station"] + top_stations_list,
                help="Select depot or starting location for field inspection team.",
            )
            start_override = None if start_station_route == "Highest Priority Station" else start_station_route
        with r_c2:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            compute_route_btn = st.button("🗺️ Compute Inspection Tour", type="primary", width='stretch', disabled=not top_stations_list)

        if "route_computed" not in st.session_state:
            st.session_state.route_computed = True

        if compute_route_btn:
            st.session_state.route_computed = True

        if st.session_state.route_computed and top_stations_list:
            route_df, total_dist = compute_inspection_route(
                route_locations,
                top_n=len(route_locations),
                start_station=start_override
            )

            rm1, rm2, rm3 = st.columns(3)
            with rm1:
                render_kpi_card("Total Route Distance", f"{total_dist:.1f} km", "Straight-line haversine", color_accent="#2DD4BF")
            with rm2:
                render_kpi_card("Average Leg Distance", f"{route_df['distance_from_prev_km'].mean():.1f} km", "Between consecutive stops", color_accent="#38BDF8")
            with rm3:
                render_kpi_card("Number of Inspection Stops", f"{len(route_df)}", "Selected priority zones", color_accent="#EF4444")

            st.warning(
                "⚠️ **Geospatial Disclaimer:** Distances shown are straight-line (haversine) calculations, NOT actual road transit routing. "
                "Actual travel times will vary based on arterial road congestion, sea links, and local traffic conditions.",
                icon=":material/warning:",
            )

            st.markdown("#### 🗺️ Route Inspection Map")
            fig_route = decision_viz.plot_inspection_route_map(route_df, selected_station)
            st.plotly_chart(fig_route, width='stretch', config=charts.CHART_CONFIG)

            st.markdown("#### 📋 Stop-by-Stop Inspection Itinerary")
            display_route = route_df[[
                "stop_number", "station", "zone", "latest_aqi",
                "priority_score", "distance_from_prev_km", "cumulative_distance_km"
            ]].rename(columns={
                "stop_number": "Stop #",
                "station": "Inspection Target",
                "zone": "Ward / Region",
                "latest_aqi": "AQI",
                "priority_score": "Score",
                "distance_from_prev_km": "Leg (km)",
                "cumulative_distance_km": "Total (km)"
            })

            st.dataframe(
                display_route,
                column_config={
                    "Stop #": st.column_config.NumberColumn("Stop #", format="#%d", width="small"),
                    "Inspection Target": st.column_config.TextColumn("Station", width="medium"),
                    "Ward / Region": st.column_config.TextColumn("Zone", width="small"),
                    "AQI": st.column_config.NumberColumn("Latest AQI", format="%.0f", width="small"),
                    "Score": st.column_config.NumberColumn("Priority", format="%.1f", width="small"),
                    "Leg (km)": st.column_config.NumberColumn("Leg (km)", format="%.2f", width="small"),
                    "Total (km)": st.column_config.NumberColumn("Total (km)", format="%.2f", width="small"),
                },
                hide_index=True,
                width='stretch',
            )

    # 4. BRIEFING EXPORT
    with dec_tab4:
        render_takeaway(
            "Generate a printable one-page executive briefing for field officers and environmental taskforces. "
            "Includes ranked zones, field directives, evidence bases, and provenance disclosures."
        )
        render_briefing_export_ui(
            priority_df=dyn_priority,
            decision_date=decision_date,
            target_date=target_date,
            weights=st.session_state.weights,
            capacity_n=capacity_n,
        )

# ==============================================================================
# SECTION 3: AIR QUALITY INSIGHTS
# ==============================================================================
elif "Air Quality Insights" in selected_nav_label:
    render_takeaway(
        f"Inspect longitudinal air quality patterns, meteorology associations, and festival pollution episodes for {selected_station}."
    )

    ins_tab1, ins_tab2, ins_tab3 = st.tabs([
        f"{ICONS['tab_discover']} Longitudinal Patterns",
        f"{ICONS['tab_weather']} Meteorology & Wind Dynamics",
        f":material/menu_book: Diwali 2023 Case Study",
    ])

    # 1. LONGITUDINAL PATTERNS
    with ins_tab1:
        st.markdown(f"### Historical Trajectory & Category Distribution: **{selected_station}**")
        st.caption("Patterns computed from verified CPCB valid monitoring days (≥18 hours of continuous readings).")

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            mean_aqi = st_daily["aqi_mean"].mean()
            render_kpi_card("Multi-Year Mean AQI", f"{mean_aqi:.1f}", "Station historical average", color_accent=get_aqi_category_color(mean_aqi)[1])
        with d2:
            max_aqi = st_daily["aqi_mean"].max()
            render_kpi_card("All-Time Peak AQI", f"{max_aqi:.0f}", f"Observed {st_daily.loc[st_daily['aqi_mean'].idxmax()]['date'].strftime('%d %b %Y')}", color_accent="#EF4444")
        with d3:
            valid_days = st_daily["is_cpcb_valid"].sum()
            render_kpi_card("CPCB Valid Days", f"{valid_days:,}", f"{valid_days/max(len(st_daily),1)*100:.1f}% completeness (≥18h)", color_accent="#10B981")
        with d4:
            coastal_str = "Coastal Zone (<2 km)" if st_daily["is_coastal"].iloc[0] == 1 else "Inland Corridor"
            render_kpi_card("Micro-Environment", st_daily["env_type"].iloc[0][:18], coastal_str, color_accent=COLORS["accent"])

        st.markdown("---")
        fig_ts = charts.plot_timeseries_trajectory(st_daily, selected_station)
        st.plotly_chart(fig_ts, width='stretch', config=charts.CHART_CONFIG)

        st.markdown("##### Historical CPCB Category Distribution (% of Monitored Days)")
        fig_dist = charts.plot_category_distribution(st_daily)
        st.plotly_chart(fig_dist, width='stretch', config=charts.CHART_CONFIG)

        st.markdown("---")
        col_seas, col_week = st.columns(2)
        with col_seas:
            fig_seas = charts.plot_seasonal_profile(st_daily)
            st.plotly_chart(fig_seas, width='stretch', config=charts.CHART_CONFIG)
        with col_week:
            fig_week = charts.plot_weekly_profile(st_daily)
            st.plotly_chart(fig_week, width='stretch', config=charts.CHART_CONFIG)

    # 2. WEATHER & WIND DYNAMICS
    with ins_tab2:
        _wind_corr_df = st_daily.dropna(subset=["aqi_mean", "wind_speed_mean"])
        _wind_aqi_corr = _wind_corr_df["wind_speed_mean"].corr(_wind_corr_df["aqi_mean"]) if len(_wind_corr_df) > 10 else float('nan')
        _corr_str = f"{_wind_aqi_corr:.2f}" if not np.isnan(_wind_aqi_corr) else "insufficient data"

        st.markdown(f"### Meteorology & Air Quality Interaction: **{selected_station}**")
        st.caption(f"Wind speed vs AQI correlation at this station: r = {_corr_str} (n={len(_wind_corr_df)} valid days). Data from Open-Meteo ERA5 reanalysis.")

        latest_w = st_daily.dropna(subset=["wind_speed_mean"]).iloc[-1]
        w1, w2, w3, w4 = st.columns(4)
        with w1:
            render_kpi_card("Surface Wind Speed", f"{latest_w['wind_speed_mean']:.1f} km/h", "10-meter ERA5 reanalysis", color_accent=COLORS["accent"])
        with w2:
            render_kpi_card("Sea-Breeze Vector (u)", f"{latest_w['wind_u_mean']:+.1f} km/h", "Positive = Westerly marine breeze", color_accent="#38BDF8")
        with w3:
            render_kpi_card("Ambient Temp (2m)", f"{latest_w['temp_mean']:.1f} °C", "Diurnal average", color_accent="#F59E0B")
        with w4:
            render_kpi_card("Relative Humidity", f"{latest_w['humidity_mean']:.0f}%", "Surface water vapor", color_accent="#10B981")

        st.markdown("---")
        w_scatter_col, w_corr_col = st.columns([1.3, 1.1])
        with w_scatter_col:
            fig_scatter = charts.plot_weather_scatter(st_daily)
            st.plotly_chart(fig_scatter, width='stretch', config=charts.CHART_CONFIG)
        with w_corr_col:
            fig_corr, dynamic_corr_insight = charts.plot_correlation_diverging(st_daily)
            st.plotly_chart(fig_corr, width='stretch', config=charts.CHART_CONFIG)
            st.caption(f"{ICONS['insight']} **Physical Insight:** {dynamic_corr_insight}")

        st.markdown("---")
        col_rose, col_rose_txt = st.columns([1.1, 1.3])
        with col_rose:
            fig_rose = charts.plot_wind_rose(st_daily)
            st.plotly_chart(fig_rose, width='stretch', config=charts.CHART_CONFIG)
        with col_rose_txt:
            st.markdown(f"##### {ICONS['compass']} Wind Directional Influx Analysis")
            st.markdown(
                """
                - **Maritime Westerlies & South-Westerlies (SW/W):** Transport clean oceanic air directly off the Arabian Sea, maintaining low AQI levels during late spring and monsoon.
                - **Continental North-Easterlies (NE/E):** Transport continental pollution and regional thermal plumes from inland Maharashtra and the Deccan Plateau, concentrating over the Mumbai basin during November–February.
                - **Stagnation Windows:** Morning boundary layer inversion suppresses vertical dispersion, concentrating vehicle exhaust along highway junctions.
                """
            )

    # 3. DIWALI CASE STUDY
    with ins_tab3:
        st.markdown("### :material/menu_book: Episode Case Study: Diwali 2023 Air Quality Surge")
        st.caption("Data period: 01 Nov – 20 Nov 2023 | Source: CPCB CAAQMS via cleaned pipeline")

        diwali_start = pd.to_datetime("2023-11-01")
        diwali_end = pd.to_datetime("2023-11-20")
        diwali_event = pd.to_datetime("2023-11-12")

        diwali_data = daily_df[
            (daily_df["date"] >= diwali_start) & (daily_df["date"] <= diwali_end)
        ].copy()

        if diwali_data.empty:
            st.warning("Diwali 2023 data not present in current benchmark extract.", icon=":material/warning:")
        else:
            pre_diwali = diwali_data[diwali_data["date"] < diwali_event]
            post_diwali = diwali_data[diwali_data["date"] >= diwali_event]

            overall_pre = pre_diwali["aqi_mean"].mean()
            overall_post = post_diwali["aqi_mean"].mean()
            delta_aqi = overall_post - overall_pre

            cs1, cs2, cs3, cs4 = st.columns(4)
            with cs1:
                render_kpi_card("Pre-Diwali Mean AQI", f"{overall_pre:.0f}", "01–11 Nov (all stations)", color_accent="#10B981" if overall_pre < 100 else "#F59E0B")
            with cs2:
                render_kpi_card("Post-Diwali Mean AQI", f"{overall_post:.0f}", "12–20 Nov (all stations)", color_accent=get_aqi_category_color(overall_post)[1])
            with cs3:
                render_kpi_card("Observed Shift", f"{delta_aqi:+.0f} AQI", "Post minus Pre episode average", color_accent="#EF4444" if delta_aqi > 0 else "#10B981")
            with cs4:
                n_exceed = (post_diwali["aqi_mean"] > 200).sum()
                render_kpi_card("Unhealthy Days (>200)", f"{n_exceed}", "Station-days post-Diwali", color_accent="#EF4444" if n_exceed > 0 else "#10B981")

            st.markdown("---")

            st_diwali = diwali_data[diwali_data["canonical_station"] == selected_station].sort_values("date")
            if not st_diwali.empty:
                import plotly.graph_objects as go
                fig_case = go.Figure()
                fig_case.add_trace(go.Scatter(
                    x=st_diwali["date"], y=st_diwali["aqi_mean"],
                    mode="lines+markers", name="Daily AQI",
                    line=dict(color=COLORS["accent"], width=2.5),
                    marker=dict(size=6),
                    hovertemplate="Date: <b>%{x|%d %b}</b><br>AQI: <b>%{y:.0f}</b><extra></extra>",
                ))
                fig_case.add_vline(x=diwali_event, line_dash="dash", line_color="#EF4444",
                                  annotation_text="Diwali Night (12 Nov)", annotation_position="top")
                fig_case.add_hline(y=200, line_dash="dot", line_color="#EF4444", line_width=1,
                                   annotation_text="Unhealthy (200)", annotation_position="bottom right")
                fig_case.update_layout(
                    title=f"Diwali 2023 Episode Trajectory: {selected_station}",
                    yaxis_title="Daily Mean AQI", height=350,
                    margin=dict(l=45, r=20, t=45, b=20),
                )
                st.plotly_chart(fig_case, width='stretch', config=charts.CHART_CONFIG)

            st.warning(
                "**Honest Evaluation Caveat:** This is an observational before/after comparison, not a controlled causal attribution. "
                "Regional meteorological shifts (e.g. boundary layer compression) occur concurrently with festival activities.",
                icon=":material/warning:",
            )

# ==============================================================================
# SECTION 4: MODEL INTELLIGENCE
# ==============================================================================
elif "Model Intelligence" in selected_nav_label:
    render_takeaway(
        "Explore honest benchmark metrics on the 2023 chronological holdout: forecast error vs persistence, "
        "severe-event detection (PR-AUC), and empirical prediction interval coverage."
    )

    mod_tab1, mod_tab2 = st.tabs([
        f"{ICONS['tab_forecast']} Forecast Diagnostics & Skill",
        f":material/verified: Validation Design & Backtesting",
    ])

    evaluation = json.loads(METRICS_PATH.read_text(encoding="utf-8")) if METRICS_PATH.exists() else {}
    latest_fc = st_preds.iloc[-1]

    # 1. FORECAST DIAGNOSTICS
    with mod_tab1:
        st.markdown(f"### Next-Day Holdout Forecast Diagnostics: **{selected_station}**")
        st.caption("Model trained on 2021–2022; tested on 2023 forward chronological holdout. No future data leakage.")

        f1, f2, f3, f4 = st.columns(4)
        with f1:
            render_kpi_card("Persistence Baseline (t-1)", f"{latest_fc['lag_1_aqi']:.0f} AQI", "Yesterday's true reading", color_accent=COLORS["text_muted"])
        with f2:
            render_kpi_card("Model Forecast", f"{latest_fc['pred_gb']:.0f} AQI", f"Delta: {latest_fc['pred_gb'] - latest_fc['lag_1_aqi']:+.0f} vs Baseline", color_accent=COLORS["accent"])
        with f3:
            cov_pct = evaluation.get("interval_coverage_pct", float("nan"))
            render_kpi_card("Nominal 80% Range", f"[{latest_fc['pred_p10']:.0f} – {latest_fc['pred_p90']:.0f}]", f"Empirical coverage: {cov_pct:.1f}%", color_accent="#38BDF8")
        with f4:
            gb_mae = evaluation.get("gradient_boosting", {}).get("MAE", float("nan"))
            baseline_mae = evaluation.get("persistence", {}).get("MAE", float("nan"))
            render_kpi_card("Model vs Baseline MAE", f"{gb_mae:.1f} vs {baseline_mae:.1f}", "Lower is better; 2023 holdout", color_accent="#F59E0B")

        st.markdown("---")
        fig_fc = charts.plot_holdout_forecast(st_preds, selected_station)
        st.plotly_chart(fig_fc, width='stretch', config=charts.CHART_CONFIG)

        # Technical diagnostics behind clean expanders
        with st.expander("🔬 Calibration Curve & Precision-Recall Analysis (AQI > 200)", expanded=False):
            st.caption("Reliability diagram shows probability calibration. PR-AUC measures skill detecting severe episodes.")
            fig_cal = charts.plot_calibration_and_pr(st_preds)
            st.plotly_chart(fig_cal, width='stretch', config=charts.CHART_CONFIG)

        with st.expander("🎯 Parity Scatter (Predicted vs Observed AQI)", expanded=False):
            st.caption("Symmetrical scatter confirms minimal systematic bias across the 2023 holdout.")
            fig_parity = charts.plot_predicted_vs_actual(st_preds)
            st.plotly_chart(fig_parity, width='stretch', config=charts.CHART_CONFIG)

        with st.expander("⚠️ Flagged Residual Anomalies (Top Forecast Shocks)", expanded=False):
            st_anomalies = st_preds[st_preds["is_anomaly"] == 1].copy()
            if not st_anomalies.empty:
                st_anomalies["Direction"] = np.where(st_anomalies["residual"] < 0, "Over-predicted", "Under-predicted")
                st_anomalies["Date_Str"] = st_anomalies["date"].dt.strftime("%Y-%m-%d")
                st_anomalies["Actual"] = st_anomalies["target_next_day_aqi"].round(0)
                st_anomalies["Forecast"] = st_anomalies["pred_gb"].round(0)
                st_anomalies["Residual"] = st_anomalies["residual"].round(1)

                disp_anom = st_anomalies[["Date_Str", "Actual", "Forecast", "Residual", "Direction", "prior_day_wind_speed_mean"]].rename(columns={
                    "Date_Str": "Date",
                    "prior_day_wind_speed_mean": "Prior Wind (km/h)",
                })
                st.dataframe(disp_anom, width='stretch', height=220, hide_index=True)
            else:
                st.info("No extreme statistical residual anomalies flagged for this station during the holdout year.")

    # 2. VALIDATION DESIGN & BACKTEST
    with mod_tab2:
        render_validation_panel(daily_df, preds_df, capacity_n=capacity_n)

# ==============================================================================
# SECTION 5: CITIZEN & REPORTS
# ==============================================================================
elif "Citizen & Reports" in selected_nav_label:
    render_takeaway(
        "Access public citizen guidance, run the interactive guided presentation demo, or review verified data source audits."
    )

    cit_tab1, cit_tab2, cit_tab3 = st.tabs([
        f":material/people: Public Citizen View",
        f":material/play_circle: Interactive Guided Demo",
        f"{ICONS['tab_methods']} Data Provenance & Methodology",
    ])

    # 1. CITIZEN VIEW
    with cit_tab1:
        st.markdown("### Public Citizen Health Advisory Mode")
        st.caption("Clear, accessible air quality indicators and actionable health guidance for vulnerable populations.")

        render_citizen_mode(
            station_data=st_daily,
            predictions=st_preds,
            station_name=selected_station,
            decision_date=decision_date,
        )

        render_aqi_card_export(
            station_name=selected_station,
            station_data=st_daily,
            decision_date=decision_date,
        )

    # 2. GUIDED DEMO
    with cit_tab2:
        st.markdown("### Interactive Evaluator & Judge Walkthrough")
        st.caption("Step-by-step walkthrough presenting the problem, hygiene pipeline, model skill, and decision ROI.")
        render_guided_demo()

    # 3. DATA PROVENANCE & METHODS
    with cit_tab3:
        st.markdown("### Verified Open Data Sources & Verification Audit")
        s1, s2 = st.columns(2)
        with s1:
            render_source_card(
                name="CPCB CAAQMS Continuous Air Quality Archive",
                provider="Central Pollution Control Board (CPCB) & MPCB",
                licence="Government Open Data (NDSAP)",
                access_date="October 2026",
                status="USED",
                fields="Hourly AQI columns, station identity and date",
                details=f"{len(daily_df):,} valid station-days across {daily_df['canonical_station'].nunique()} stations; 18-hour validity threshold applied.",
            )
            render_source_card(
                name="Open-Meteo Historical Weather Archive",
                provider="Open-Meteo GmbH (ERA5 Reanalysis)",
                licence="Creative Commons Attribution 4.0 (CC BY 4.0)",
                access_date="October 2026",
                status="USED",
                fields="temperature_2m, relative_humidity_2m, wind_u, wind_v, pressure, rain",
                details="Continuous hourly surface weather matching Mumbai coordinates (19.076°N, 72.878°E).",
            )

        with s2:
            render_source_card(
                name="OpenStreetMap Spatial Context & Infrastructure",
                provider="OpenStreetMap Foundation (Overpass API)",
                licence="Open Database License 1.0 (ODbL)",
                access_date="October 2026",
                status="USED",
                fields="highway=primary/secondary, landuse=industrial/construction, coastline",
                details="Contextual table covers station environs; completeness varies across stations.",
            )
            render_source_card(
                name="OpenAQ REST API v3",
                provider="OpenAQ Inc.",
                licence="CC BY 4.0",
                access_date="October 2026",
                status="REJECTED",
                fields="N/A (API Key Mandate)",
                details="Excluded to ensure zero-key reproducibility from a fresh clone.",
            )

        st.markdown("---")
        st.markdown("### End-to-End Decision Architecture")
        st.markdown(
            """
            ```
            [ CPCB CAAQMS Data ]  +  [ Open-Meteo Weather ]  +  [ OpenStreetMap Landuse ]
                     │                          │                         │
                     ▼                          ▼                         ▼
            ┌────────────────────────────────────────────────────────────────────────┐
            │ 1. DATA HYGIENE: Sensor-stuck filter, 18-hour rule, gap interpolation   │
            └───────────────────────────────────┬────────────────────────────────────┘
                                                ▼
            ┌────────────────────────────────────────────────────────────────────────┐
            │ 2. DECISION-TIME FEATURES: 7-day rolling stats and prior-day weather  │
            └───────────────────────────────────┬────────────────────────────────────┘
                                                ▼
            ┌────────────────────────────────────────────────────────────────────────┐
            │ 3. ANALYTICAL MODELS: Ridge, GBDT, Quantile Intervals & Classifier     │
            └───────────────────────────────────┬────────────────────────────────────┘
                                                ▼
            ┌────────────────────────────────────────────────────────────────────────┐
            │ 4. DECISION ENGINE: Multi-criteria Priority Score & Resource Allocation│
            └────────────────────────────────────────────────────────────────────────┘
            ```
            """
        )

        with st.expander(":material/terminal: How to Reproduce from a Fresh Clone", expanded=False):
            st.code("""
git clone <repo-url> && cd citypulse
pip install -r requirements.txt
make data
make model
streamlit run app.py
            """, language="bash")

        with st.expander(":material/warning: Known Limitations & Disclosures", expanded=False):
            st.markdown("""
1. **Model does not beat persistence on MAE.** Daily AQI is heavily autoregressive; persistence is a tough baseline.
2. **80% interval undercoverage.** Empirical coverage is ~73.8%. Treat as exploratory uncertainty bounds.
3. **Sparse station network.** ~18–30 stations citywide; spatial interpolation has uncertainty between sensors.
4. **Gridded weather.** ERA5 reanalysis is gridded (~25 km); hyper-local micro-climate eddies may be missed.
5. **Historical replay only.** Observations reflect benchmark training dataset; not live real-time sensors.
            """)

# Persistent Command Center Footer
render_footer()
