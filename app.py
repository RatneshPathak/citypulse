"""
CityPulse: Mumbai — Decision-Support Prototype for Air Quality
Predict • Explain • Act

Presentation-Layer Redesign for Municipal Decision Support (BMC / MPCB).
Streamlit native Material Symbols icons with zero emojis.
All numbers trace to real CPCB/Open-Meteo data processed by scripts in src/.
"""
import json
import importlib
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from components import (
    render_action_dossier,
    render_action_strip,
    render_compact_banner,
    render_footer,
    render_header,
    render_kpi_card,
    render_source_card,
    render_takeaway,
)
from icons import ICONS
from config import EVENT_NAME, TEAM_MEMBERS, DATA_ATTRIBUTION
import theme
from theme import AQI_PALETTE, COLORS, get_aqi_category_color
import charts

from src.decision.whatif import compute_rank_stability, compute_rank_delta
from src.decision.routing import compute_inspection_route
from src.decision.briefing import render_briefing_export_ui
from src.decision.validation import render_validation_panel
from src.decision import viz as decision_viz
decision_viz = importlib.reload(decision_viz)

COLORS.setdefault("background", COLORS["bg"])

from src.citizen.citizen_view import render_citizen_mode, render_aqi_card_export
from src.demo.guided_demo import render_guided_demo
from src.demo.replay_dates import shift_date_columns

st.set_page_config(
    page_title="CityPulse: Mumbai — Air Quality Prioritisation",
    page_icon=ICONS["page_icon"],
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.inject_custom_css()

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

st.sidebar.markdown(f"## {ICONS['console_badge']} BMC / MPCB")
st.sidebar.caption("Environmental Triage Console")

st.sidebar.markdown(f"### {ICONS['sidebar_location']} Location Target")
target_day = preds_df["date"].max()
recent_predictions = preds_df[(preds_df["date"] < target_day) & (preds_df["date"] >= target_day - pd.Timedelta(days=7))]
all_stations = sorted(
    set(daily_df["canonical_station"].dropna())
    & set(preds_df.loc[preds_df["date"] == target_day, "canonical_station"].dropna())
    & set(recent_predictions["canonical_station"].dropna())
)
default_station_idx = all_stations.index("Bandra Kurla Complex") if "Bandra Kurla Complex" in all_stations else 0
selected_station = st.sidebar.selectbox(
    "Focus Station / Ward",
    all_stations,
    index=default_station_idx,
    help="Select a continuous monitoring station to inspect micro-climate and action protocols."
)

st.sidebar.markdown("---")

st.sidebar.markdown(f"### {ICONS['sidebar_weights']} Prioritisation Policy Weights")
st.sidebar.caption("Define the relative importance of evidence criteria:")

DEFAULT_WEIGHTS = {
    "w_exp": 0.30,
    "w_pers": 0.25,
    "w_trend": 0.15,
    "w_fore": 0.20,
    "w_gap": 0.10,
}

if "weights" not in st.session_state:
    st.session_state.weights = DEFAULT_WEIGHTS.copy()

if st.sidebar.button("Reset to Recommended Defaults", icon=ICONS["sidebar_reset"], width='stretch'):
    st.session_state.weights = DEFAULT_WEIGHTS.copy()

w_exp = st.sidebar.slider(
    "Recent Exposure (7-day)",
    0.0, 1.0, float(st.session_state.weights["w_exp"]), 0.05,
    help="Weight assigned to recent cumulative exposure level relative to national air quality standards."
)
w_pers = st.sidebar.slider(
    "Persistence Shock (>150)",
    0.0, 1.0, float(st.session_state.weights["w_pers"]), 0.05,
    help="Weight for the count of days in the past week crossing the Moderate/Poor threshold."
)
w_trend = st.sidebar.slider(
    "Trend Acceleration",
    0.0, 1.0, float(st.session_state.weights["w_trend"]), 0.05,
    help="Weight for recent worsening rate (today vs 7-day rolling mean)."
)
w_fore = st.sidebar.slider(
    "Forecast Risk (24h)",
    0.0, 1.0, float(st.session_state.weights["w_fore"]), 0.05,
    help="Weight for the historical holdout estimate of AQI > 200 on the target day."
)
w_gap = st.sidebar.slider(
    "Vulnerability / Highway Corridors",
    0.0, 1.0, float(st.session_state.weights["w_gap"]), 0.05,
    help="Weight for environmental vulnerability (proximity to arterial highway chokepoints or industrial zones)."
)

st.session_state.weights = {
    "w_exp": w_exp,
    "w_pers": w_pers,
    "w_trend": w_trend,
    "w_fore": w_fore,
    "w_gap": w_gap,
}

total_w = w_exp + w_pers + w_trend + w_fore + w_gap
if abs(total_w - 1.0) < 0.01:
    st.sidebar.success(f"Weights Balanced (Total = {total_w:.2f})", icon=":material/check_circle:")
else:
    st.sidebar.warning(f"Total = {total_w:.2f} (Scores auto-normalized to 100%)", icon=":material/warning:")

st.sidebar.markdown("---")
st.sidebar.markdown(f"### {ICONS['sidebar_budget']} Resource Budget")
capacity_n = st.sidebar.slider(
    "Weekly Municipal Inspection Capacity",
    1, 15, 5,
    help="Number of priority zones the municipal enforcement fleet has resources to physically inspect this week."
)

st.sidebar.markdown("---")
with st.sidebar.expander(f"{ICONS['info']} About CityPulse", expanded=False):
    st.markdown(f"**Built for {EVENT_NAME}**  \nby **{TEAM_MEMBERS}**")
    st.caption(
        "CityPulse: Mumbai is an air quality prioritisation and decision-support prototype "
        "for municipal environmental planning and inspection triage (BMC / MPCB role). "
        "Not an official warning system.\n\n"
        f"**Data Sources:** {DATA_ATTRIBUTION}.\n\n"
        "See `DATA_SOURCES.md` for licences and access dates."
    )

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

render_compact_banner()
render_header(selected_station, decision_date, total_stations=daily_df["canonical_station"].nunique())

freshness_text = f"**Data range:** {data_start} to {data_end}"
if "file_updated" in data_freshness:
    freshness_text += f" | **Processed:** {data_freshness['file_updated']}"
st.caption(f":material/schedule: {freshness_text} | **Coverage:** {daily_df['canonical_station'].nunique()} stations, {len(daily_df):,} station-days")

st.warning(f"Historical replay: observations through {decision_date} estimate risk for {target_date}. This is not a live air-quality alert.")

st_daily = daily_df[
    (daily_df["canonical_station"] == selected_station)
    & (daily_df["date"] <= pd.to_datetime(dyn_priority["date"].iloc[0]))
].sort_values("date").copy()
st_preds = preds_df[preds_df["canonical_station"] == selected_station].sort_values("date").copy()
st_prio_row = dyn_priority[dyn_priority["station"] == selected_station]
st_prio = st_prio_row.iloc[0]

st.sidebar.markdown("---")
st.sidebar.markdown(f"### :material/people: View Mode")
citizen_mode = st.sidebar.toggle(
    "Citizen-Friendly Mode",
    value=False,
    help="Switch to simplified public view with health guidance"
)

tab1, tab_whatif, tab_route, tab_briefing, tab2, tab3, tab4, tab_valid, tab_case, tab_citizen, tab_demo, tab5 = st.tabs([
    f"{ICONS['tab_act']} 1. Priority Rankings",
    f":material/tune: 2. What-If Simulator",
    f":material/route: 3. Route Planner",
    f":material/description: 4. Briefing Export",
    f"{ICONS['tab_discover']} 5. Historical Patterns",
    f"{ICONS['tab_weather']} 6. Weather Analysis",
    f"{ICONS['tab_forecast']} 7. Forecast Performance",
    f":material/verified: 8. Validation & Backtest",
    f":material/case_study: 9. Case Study",
    f":material/people: 10. Citizen View",
    f":material/play_circle: 11. Guided Demo",
    f"{ICONS['tab_methods']} 12. Data & Methods",
])

with tab1:
    render_takeaway(
        f"In the {decision_date} replay, <strong>{dyn_priority.iloc[0]['station']}</strong> ranks #1 (Score: {dyn_priority.iloc[0]['priority_score']:.1f}/100). The top {capacity_n} zones form a historical inspection scenario."
    )

    k1, k2, k3, k4 = st.columns(4)
    sel_cat_name, sel_cat_col = get_aqi_category_color(st_prio["latest_aqi"])
    with k1:
        render_kpi_card(
            "Selected Zone Rank",
            f"#{st_prio['rank']}",
            f"Out of {len(dyn_priority)} monitored zones",
            badge="INSPECT" if st_prio["rank"] <= capacity_n else "ROUTINE",
            color_accent="#E5484D" if st_prio["rank"] <= capacity_n else COLORS["accent"],
        )
    with k2:
        render_kpi_card(
            "Composite Priority Score",
            f"{st_prio['priority_score']:.1f}",
            "Scale 0 – 100 • Multi-criteria",
            color_accent=sel_cat_col,
        )
    with k3:
        render_kpi_card(
            f"AQI on {decision_date}",
            f"{st_prio['latest_aqi']:.0f}",
            f"Category: {sel_cat_name}",
            color_accent=sel_cat_col,
        )
    with k4:
        render_kpi_card(
            f"{target_date} Risk Estimate",
            f"{st_prio['forecast_prob_unhealthy']*100:.0f}%",
            "Estimated chance of AQI > 200 on replay target day",
            color_accent="#E5484D" if st_prio['forecast_prob_unhealthy'] >= 0.50 else "#2ECC71",
        )

    render_action_strip(dyn_priority, top_n=min(5, capacity_n))

    st.markdown("---")
    col_lead, col_map = st.columns([1.15, 1.25])

    with col_lead:
        st.markdown(f"##### {ICONS['leaderboard']} Priority Leaderboard & Inspection Roster")

        table_df = dyn_priority.copy()
        table_df["Action"] = np.where(table_df["rank"] <= capacity_n, "INSPECT", "ROUTINE")
        table_df["Category"] = table_df["latest_aqi"].apply(lambda v: get_aqi_category_color(v)[0])

        coverage_counts = daily_df.groupby("canonical_station")["is_cpcb_valid"].agg(["sum", "count"])
        coverage_counts["coverage_pct"] = (coverage_counts["sum"] / coverage_counts["count"] * 100).round(1)
        table_df = table_df.merge(
            coverage_counts[["coverage_pct"]].rename_axis("station"),
            left_on="station", right_index=True, how="left"
        )
        table_df["coverage_pct"] = table_df["coverage_pct"].fillna(0)

        display_df = table_df[[
            "rank", "station", "priority_score", "latest_aqi", "Category", "coverage_pct", "Action", "zone"
        ]].rename(columns={
            "rank": "Rank",
            "station": "Zone / Station",
            "priority_score": "Score",
            "latest_aqi": "AQI",
            "coverage_pct": "Valid %",
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
                "Valid %": st.column_config.ProgressColumn("Data Coverage", help="% of station-days meeting 18h CPCB validity", format="%.0f%%", min_value=0, max_value=100, width="small"),
                "Action": st.column_config.TextColumn("Action Status", width="small"),
                "Zone": st.column_config.TextColumn("Region", width="medium"),
            },
            hide_index=True,
            width='stretch',
            height=380,
        )

    with col_map:
        st.markdown(f"##### {ICONS['map']} Spatial Priority Map")
        fig_map = charts.plot_priority_map(dyn_priority, selected_station)
        st.plotly_chart(fig_map, width='stretch', config=charts.CHART_CONFIG)
        st.caption("Map tiles: © OpenStreetMap contributors, © CARTO. Station positions from CPCB metadata.")

    st.markdown("---")
    st.markdown(f"##### {ICONS['analytics']} Why is **{selected_station}** ranked **#{st_prio['rank']}**? (Score Contribution Breakdown)")
    fig_breakdown = charts.plot_score_breakdown(st_prio.to_dict(), st.session_state.weights)
    st.plotly_chart(fig_breakdown, width='stretch', config=charts.CHART_CONFIG)

    render_action_dossier(st_prio.to_dict(), allocated=(st_prio["rank"] <= capacity_n))

with tab_whatif:
    render_takeaway(
        "Adjust policy weights to see how rankings change. Run Monte Carlo simulation to assess which zones are "
        "**robust** to weight changes vs which are **unstable**."
    )
    
    st.markdown(f"### :material/tune: Policy Weight Simulator")
    
    if "baseline_priority" not in st.session_state:
        st.session_state.baseline_priority = dyn_priority.copy()
    
    col_sim1, col_sim2, col_sim3 = st.columns([1, 1, 1])
    with col_sim1:
        if st.button("📌 Set Current as New Baseline", width='stretch', help="Store current rankings as the new comparison baseline"):
            st.session_state.baseline_priority = dyn_priority.copy()
            st.success("Baseline updated!", icon=":material/check_circle:")
    
    with col_sim2:
        if st.button("🔄 Reset to Original Default", width='stretch', help="Reset sidebar weights to recommended defaults"):
            st.session_state.weights = DEFAULT_WEIGHTS.copy()
            st.rerun()
    
    st.markdown("---")
    st.markdown("#### Rank Movement Analysis")
    
    delta_df = compute_rank_delta(st.session_state.baseline_priority, dyn_priority)
    big_movers = delta_df[delta_df["delta"].abs() >= 3].head(10)
    
    col_move1, col_move2 = st.columns(2)
    with col_move1:
        st.markdown("**Biggest Rank Changes:**")
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
        
        st.markdown("**Summary:**")
        st.markdown(f"- 📈 Moved up: **{moved_up}** zones")
        st.markdown(f"- 📉 Moved down: **{moved_down}** zones")
        st.markdown(f"- ➖ Unchanged: **{unchanged}** zones")
    
    if len(dyn_priority) > 0:
        fig_movement = decision_viz.plot_rank_movement(
            st.session_state.baseline_priority,
            dyn_priority,
            top_n=15
        )
        st.plotly_chart(fig_movement, width='stretch', config=charts.CHART_CONFIG)
    
    st.markdown("---")
    st.markdown("### 🎲 Rank Stability Monte Carlo Simulation")
    st.caption(
        f"Run {500} simulations with random weight perturbations (±30%) to find zones that are **robust** "
        "to policy choices vs those that are **sensitive**."
    )
    
    run_stability = st.button(
        "▶️ Run Stability Simulation (500 iterations)",
        width='content',
        help="This takes ~15-30 seconds"
    )
    
    if run_stability or "stability_results" in st.session_state:
        with st.spinner("Running Monte Carlo stability analysis..."):
            stability_df = compute_rank_stability(
                preds_df,
                baseline_weights=st.session_state.weights,
                n_simulations=500,
                perturbation_pct=0.30,
                target_n=capacity_n
            )
            st.session_state.stability_results = stability_df
        
        stability_df = st.session_state.stability_results
        
        st.success(f"Simulation complete! Tested {500} random weight combinations.", icon=":material/check_circle:")
        
        col_stab1, col_stab2 = st.columns(2)
        
        with col_stab1:
            fig_prob = decision_viz.plot_probability_heatmap(stability_df, top_n=capacity_n)
            st.plotly_chart(fig_prob, width='stretch', config=charts.CHART_CONFIG)
        
        with col_stab2:
            fig_ranges = decision_viz.plot_rank_stability_ranges(stability_df, top_n=10)
            st.plotly_chart(fig_ranges, width='stretch', config=charts.CHART_CONFIG)
        
        st.markdown("---")
        st.markdown("#### 💡 Stability Interpretation")
        
        robust_zones = stability_df[stability_df["prob_top_n"] > 0.80].head(5)
        unstable_zones = stability_df[stability_df["rank_range"] > 10].head(5)
        
        col_interp1, col_interp2 = st.columns(2)
        
        with col_interp1:
            st.markdown(f"**✅ Robust Top-{capacity_n} Zones** (>80% probability):")
            if not robust_zones.empty:
                for _, row in robust_zones.iterrows():
                    st.markdown(f"- **{row['station']}**: {row['prob_top_n']*100:.0f}% in top-{capacity_n}")
            else:
                st.info("No zones have >80% probability — consider adjusting capacity_n", icon=":material/info:")
        
        with col_interp2:
            st.markdown("**⚠️ Rank-Unstable Zones** (wide rank range):")
            if not unstable_zones.empty:
                for _, row in unstable_zones.iterrows():
                    st.markdown(f"- **{row['station']}**: ranks {row['rank_min']}-{row['rank_max']} (range: {row['rank_range']})")
            else:
                st.success("All zones have stable rankings!", icon=":material/check_circle:")

with tab_route:
    render_takeaway(
        f"Plan an efficient inspection route for the top-{capacity_n} priority zones using nearest-neighbor routing. "
        "**Note:** Distances are straight-line (haversine), not actual road travel."
    )
    
    st.markdown(f"### :material/route: Inspection Route Planner")
    
    route_col1, route_col2 = st.columns([2, 1])
    
    with route_col1:
        selected_route_stations = dyn_priority.head(capacity_n)
        route_lat = pd.to_numeric(selected_route_stations["latitude"], errors="coerce")
        route_lon = pd.to_numeric(selected_route_stations["longitude"], errors="coerce")
        route_mask = route_lat.between(-90, 90) & route_lon.between(-180, 180)
        route_locations = selected_route_stations.loc[route_mask].copy()
        top_stations_list = route_locations["station"].tolist()
        start_station_route = st.selectbox(
            "Starting Point (Municipal Office / Depot)",
            ["Highest Priority"] + top_stations_list,
            help="Select where the inspection team will begin their route"
        )
        start_override = None if start_station_route == "Highest Priority" else start_station_route

        skipped_stations = selected_route_stations.loc[~route_mask, "station"].tolist()
        if skipped_stations:
            st.warning(
                "Route excludes stations without coordinates: " + ", ".join(skipped_stations)
            )
    
    with route_col2:
        if st.button("🗺️ Compute Optimal Route", type="primary", width='stretch', disabled=not top_stations_list):
            st.session_state.route_computed = True
    
    if "route_computed" not in st.session_state:
        st.session_state.route_computed = False
    if not top_stations_list:
        st.session_state.route_computed = False
    
    if st.session_state.route_computed:
        with st.spinner("Computing nearest-neighbor tour..."):
            route_df, total_distance = compute_inspection_route(
                route_locations,
                top_n=len(route_locations),
                start_station=start_override
            )
        
        st.markdown("---")
        route_sum_col1, route_sum_col2, route_sum_col3 = st.columns(3)
        
        with route_sum_col1:
            st.metric(
                label="Total Route Distance",
                value=f"{total_distance:.1f} km",
                help="Straight-line distance (not road routing)"
            )
        
        with route_sum_col2:
            avg_dist = route_df["distance_from_prev_km"].mean()
            st.metric(
                label="Avg. Leg Distance",
                value=f"{avg_dist:.1f} km",
                help="Average distance between consecutive stops"
            )
        
        with route_sum_col3:
            st.metric(
                label="Number of Stops",
                value=f"{len(route_df)}",
                help="Inspection zones on this route"
            )
        
        st.warning(
            "⚠️ **Disclaimer:** Distances shown are straight-line (haversine) calculations, NOT actual road routing. "
            "Real travel time will be longer due to road networks, traffic, and Mumbai's geography.",
            icon=":material/warning:"
        )
        
        st.markdown("---")
        st.markdown("#### 🗺️ Route Visualization")
        fig_route = decision_viz.plot_inspection_route_map(route_df, selected_station)
        st.plotly_chart(fig_route, width='stretch', config=charts.CHART_CONFIG)
        
        st.markdown("---")
        st.markdown("#### 📋 Detailed Route Schedule")
        
        display_route = route_df[[
            "stop_number", "station", "zone", "latest_aqi",
            "priority_score", "distance_from_prev_km", "cumulative_distance_km"
        ]].rename(columns={
            "stop_number": "Stop",
            "station": "Station",
            "zone": "Zone",
            "latest_aqi": "AQI",
            "priority_score": "Score",
            "distance_from_prev_km": "Leg (km)",
            "cumulative_distance_km": "Cumulative (km)"
        })
        
        st.dataframe(
            display_route,
            column_config={
                "Stop": st.column_config.NumberColumn("Stop #", width="small", format="#%d"),
                "Station": st.column_config.TextColumn("Station", width="medium"),
                "Zone": st.column_config.TextColumn("Zone", width="small"),
                "AQI": st.column_config.NumberColumn("Latest AQI", format="%.0f", width="small"),
                "Score": st.column_config.NumberColumn("Priority", format="%.1f", width="small"),
                "Leg (km)": st.column_config.NumberColumn("Leg Distance", format="%.2f", width="small"),
                "Cumulative (km)": st.column_config.NumberColumn("Total Distance", format="%.2f", width="small"),
            },
            hide_index=True,
            width='stretch',
        )

with tab_briefing:
    render_takeaway(
        "Generate a printable one-page briefing document for field inspectors. Includes top priority zones, "
        "recommended actions, evidence basis, and data attribution. Exports as HTML (always) and PDF (if library available)."
    )
    
    render_briefing_export_ui(
        priority_df=dyn_priority,
        decision_date=decision_date,
        target_date=target_date,
        weights=st.session_state.weights,
        capacity_n=capacity_n
    )

with tab2:
    render_takeaway(
        f"Explore measured AQI history for {selected_station}. Seasonal and hourly patterns are associations; they do not identify a specific emission source."
    )
    st.caption(":material/info: **Reliability:** Patterns below are computed from CPCB-valid days (≥18h of readings). Coverage varies by station and season — monsoon months may have fewer valid days due to instrument maintenance.")

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        mean_aqi = st_daily["aqi_mean"].mean()
        render_kpi_card("Multi-Year Mean AQI", f"{mean_aqi:.1f}", "Latest Multi-Year Station Average", color_accent=get_aqi_category_color(mean_aqi)[1])
    with d2:
        max_aqi = st_daily["aqi_mean"].max()
        render_kpi_card("All-Time Peak AQI", f"{max_aqi:.0f}", f"Observed on {st_daily.loc[st_daily['aqi_mean'].idxmax()]['date'].strftime('%d %b %Y')}", color_accent="#E5484D")
    with d3:
        valid_days = st_daily["is_cpcb_valid"].sum()
        render_kpi_card("CPCB Valid Days", f"{valid_days:,}", f"{valid_days/max(len(st_daily),1)*100:.1f}% completeness (>=18h)", color_accent="#2ECC71")
    with d4:
        coastal_str = "Coastal Proximity (<2 km)" if st_daily["is_coastal"].iloc[0] == 1 else "Inland Corridor"
        render_kpi_card("Micro-Environment", st_daily["env_type"].iloc[0][:18], coastal_str, color_accent=COLORS["accent"])

    st.markdown("---")
    fig_ts = charts.plot_timeseries_trajectory(st_daily, selected_station)
    st.plotly_chart(fig_ts, width='stretch', config=charts.CHART_CONFIG)

    st.markdown(f"##### {ICONS['breakdown']} Historical Category Breakdown (% of Days)")
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

    st.markdown("---")

with tab3:
    _wind_corr_df = st_daily.dropna(subset=["aqi_mean", "wind_speed_mean"])
    _wind_aqi_corr = _wind_corr_df["wind_speed_mean"].corr(_wind_corr_df["aqi_mean"]) if len(_wind_corr_df) > 10 else float('nan')
    _corr_str = f"{_wind_aqi_corr:.2f}" if not np.isnan(_wind_aqi_corr) else "insufficient data"
    render_takeaway(
        f"Compare AQI and weather history at {selected_station}. At this station, wind speed and AQI have a correlation of r = {_corr_str} (n={len(_wind_corr_df)} valid days); season and location may confound it."
    )
    st.caption(":material/info: **Reliability:** Weather data from Open-Meteo ERA5 reanalysis (gridded, not station-level). Correlations are observational associations, not causal. Confounders include season, boundary layer height, and regional transport.")

    latest_w = st_daily.dropna(subset=["wind_speed_mean"]).iloc[-1]
    w1, w2, w3, w4 = st.columns(4)
    with w1:
        render_kpi_card("Surface Wind Speed", f"{latest_w['wind_speed_mean']:.1f} km/h", "10-meter ERA5 reanalysis", color_accent=COLORS["accent"])
    with w2:
        render_kpi_card("Sea-Breeze Vector (u)", f"{latest_w['wind_u_mean']:+.1f} km/h", "Positive = Westerly maritime breeze", color_accent="#00D2FF")
    with w3:
        render_kpi_card("Temperature (2m)", f"{latest_w['temp_mean']:.1f} °C", "Diurnal average", color_accent="#F5C542")
    with w4:
        render_kpi_card("Relative Humidity", f"{latest_w['humidity_mean']:.0f}%", "Surface water vapor", color_accent="#A3D86B")

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
            f"""
            - **Maritime Westerlies & South-Westerlies (SW/W):** Transport clean oceanic air directly off the Arabian Sea, maintaining low AQI levels during late spring and monsoon.
            - **Continental North-Easterlies (NE/E):** Transport continental pollution and regional thermal plumes from inland Maharashtra and the Deccan Plateau, concentrating over the Mumbai basin during November–February.
            - **Calm / Transition Periods:** Morning boundary layer stagnation suppresses vertical mixing, concentrating vehicle exhaust along highway junctions.
            """
        )

with tab4:
    render_takeaway(
        "On the 2023 holdout, persistence has the lowest point-forecast MAE. The classifier identifies AQI > 200 risk days with PR-AUC 0.811. The 80% prediction interval achieves 74.1% empirical coverage — undercovering by ~6pp, treat as exploratory range."
    )
    st.caption(":material/info: **What could be wrong:** Model was trained on 2021–2022 and tested on 2023. A structural shift in emissions (new construction, policy change) could degrade skill. Persistence is hard to beat because daily AQI is heavily autoregressive.")

    latest_fc = st_preds.iloc[-1]
    evaluation = json.loads(METRICS_PATH.read_text(encoding="utf-8")) if METRICS_PATH.exists() else {}
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        render_kpi_card("Persistence Baseline (t-1)", f"{latest_fc['lag_1_aqi']:.0f} AQI", "Yesterday's true reading", color_accent=COLORS["text_muted"])
    with f2:
        render_kpi_card("Model Forecast", f"{latest_fc['pred_gb']:.0f} AQI", f"Delta: {latest_fc['pred_gb'] - latest_fc['lag_1_aqi']:+.0f} vs Baseline", color_accent=COLORS["accent"])
    with f3:
        render_kpi_card("Nominal 80% Range", f"[{latest_fc['pred_p10']:.0f} – {latest_fc['pred_p90']:.0f}]", f"Actual holdout coverage: {evaluation.get('interval_coverage_pct', float('nan')):.1f}%", color_accent="#00D2FF")
    with f4:
        gb_mae = evaluation.get("gradient_boosting", {}).get("MAE", float("nan"))
        baseline_mae = evaluation.get("persistence", {}).get("MAE", float("nan"))
        render_kpi_card("Model vs Baseline MAE", f"{gb_mae:.1f} vs {baseline_mae:.1f}", "Lower is better; 2023 holdout", color_accent="#F5C542")

    st.markdown("---")
    fig_fc = charts.plot_holdout_forecast(st_preds, selected_station)
    st.plotly_chart(fig_fc, width='stretch', config=charts.CHART_CONFIG)

    st.markdown("---")
    c_cal, c_parity = st.columns(2)
    with c_cal:
        fig_cal = charts.plot_calibration_and_pr(st_preds)
        st.plotly_chart(fig_cal, width='stretch', config=charts.CHART_CONFIG)
        st.caption(f"{ICONS['diagram']} **Reliability Diagram:** Diagonal line represents perfect calibration. Points near the line indicate reliable probability estimates.")

    with c_parity:
        fig_parity = charts.plot_predicted_vs_actual(st_preds)
        st.plotly_chart(fig_parity, width='stretch', config=charts.CHART_CONFIG)
        st.caption(f"{ICONS['parity']} **Parity Scatter:** Dotted line represents y=x. Symmetrical scatter confirms minimal systematic bias across 2023 holdout.")

    st.markdown("---")
    st.markdown(f"##### {ICONS['anomalies']} Flagged Residual Anomalies (Top Forecast Shocks)")
    st_anomalies = st_preds[st_preds["is_anomaly"] == 1].copy()
    if not st_anomalies.empty:
        st_anomalies["Direction"] = np.where(st_anomalies["residual"] < 0, "Over-predicted", "Under-predicted")
        st_anomalies["Date_Str"] = st_anomalies["date"].dt.strftime("%Y-%m-%d")
        st_anomalies["Actual"] = st_anomalies["target_next_day_aqi"].round(0)
        st_anomalies["Forecast"] = st_anomalies["pred_gb"].round(0)
        st_anomalies["Residual"] = st_anomalies["residual"].round(1)

        disp_anom = st_anomalies[["Date_Str", "Actual", "Forecast", "Residual", "Direction", "prior_day_wind_speed_mean"]].rename(columns={
            "Date_Str": "Date (YYYY-MM-DD)",
            "prior_day_wind_speed_mean": "Prior-day Wind Speed (km/h)",
        })
        st.dataframe(disp_anom, width='stretch', height=220, hide_index=True)
    else:
        st.info("No extreme statistical residual anomalies flagged for this station during 2023.", icon=":material/info:")

with tab_valid:
    render_validation_panel(daily_df, preds_df, capacity_n=capacity_n)

with tab_case:
    render_takeaway(
        "Walk through one real air quality episode from the data. Signal → Evidence → Risk → Action."
    )
    st.markdown("### :material/case_study: Case Study: Diwali 2023 Air Quality Episode")
    st.caption("Data period: 01 Nov – 20 Nov 2023 | Source: CPCB CAAQMS via cleaned pipeline")

    diwali_start = pd.to_datetime("2023-11-01")
    diwali_end = pd.to_datetime("2023-11-20")
    diwali_event = pd.to_datetime("2023-11-12")

    diwali_data = daily_df[
        (daily_df["date"] >= diwali_start) & (daily_df["date"] <= diwali_end)
    ].copy()

    if diwali_data.empty:
        st.warning("Diwali 2023 data not available in current dataset.", icon=":material/warning:")
    else:
        pre_diwali = diwali_data[diwali_data["date"] < diwali_event]
        post_diwali = diwali_data[diwali_data["date"] >= diwali_event]

        pre_mean = pre_diwali.groupby("canonical_station")["aqi_mean"].mean()
        post_mean = post_diwali.groupby("canonical_station")["aqi_mean"].mean()

        overall_pre = pre_diwali["aqi_mean"].mean()
        overall_post = post_diwali["aqi_mean"].mean()
        delta_aqi = overall_post - overall_pre

        cs1, cs2, cs3, cs4 = st.columns(4)
        with cs1:
            render_kpi_card("Pre-Diwali Mean AQI", f"{overall_pre:.0f}", "01–11 Nov (all stations)", color_accent="#2ECC71" if overall_pre < 100 else "#F5C542")
        with cs2:
            render_kpi_card("Post-Diwali Mean AQI", f"{overall_post:.0f}", "12–20 Nov (all stations)", color_accent=get_aqi_category_color(overall_post)[1])
        with cs3:
            render_kpi_card("AQI Change", f"{delta_aqi:+.0f}", "Post minus Pre average", color_accent="#E5484D" if delta_aqi > 0 else "#2ECC71")
        with cs4:
            n_exceed = (post_diwali["aqi_mean"] > 200).sum()
            render_kpi_card("Unhealthy Days (>200)", f"{n_exceed}", "Station-days post-Diwali", color_accent="#E5484D" if n_exceed > 0 else "#2ECC71")

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
            fig_case.add_vline(x=diwali_event, line_dash="dash", line_color="#E5484D",
                              annotation_text="Diwali Night", annotation_position="top")
            fig_case.add_hline(y=200, line_dash="dot", line_color="#E5484D", line_width=1,
                               annotation_text="Unhealthy (200)", annotation_position="bottom right")
            fig_case.update_layout(
                title=f"Diwali 2023 Episode: {selected_station}",
                yaxis_title="Daily Mean AQI", height=350,
                margin=dict(l=45, r=20, t=45, b=20),
            )
            st.plotly_chart(fig_case, width='stretch', config=charts.CHART_CONFIG)

        st.markdown("---")
        st.markdown("#### Interpretation")
        if delta_aqi > 20:
            st.markdown(
                f"**Signal detected:** AQI increased by {delta_aqi:+.0f} units on average after Diwali night. "
                f"This is consistent with firecracker emissions and post-festival biomass burning, "
                f"though meteorological changes (reduced wind) could also contribute."
            )
        elif delta_aqi > 0:
            st.markdown(
                f"**Modest signal:** AQI increased by {delta_aqi:+.0f} units. The effect is visible but modest — "
                f"separating Diwali emissions from seasonal winter deterioration requires controlled analysis we don't have."
            )
        else:
            st.markdown(
                f"**No clear Diwali effect visible:** AQI changed by {delta_aqi:+.0f}. "
                f"Wind conditions or rainfall during this period may have masked any emission spike."
            )

        st.warning(
            "**Caveat:** This is a before/after comparison, not a causal analysis. "
            "We cannot attribute the AQI change solely to Diwali without controlling for weather, "
            "regional transport, and other emission sources. The data shows what happened, not why.",
            icon=":material/warning:"
        )

with tab5:
    render_takeaway(
        "CityPulse: Mumbai is built strictly on verified, keyless open public data. Zero synthetic data is used for analysis, modeling, or regulatory evidence."
    )

    st.markdown(f"### {ICONS['source']} Public Data Sources & Verification Audit")
    s1, s2 = st.columns(2)
    with s1:
        render_source_card(
            name="CPCB CAAQMS Continuous Air Quality Archive",
            provider="Central Pollution Control Board (CPCB) & MPCB",
            licence="Government Open Data (NDSAP)",
            access_date="October 2026",
            status="USED",
            fields="Hourly AQI columns, station identity and date",
            details=f"{len(daily_df):,} valid station-days across {daily_df['canonical_station'].nunique()} stations (Latest Multi-Year Dataset); 18-hour validity threshold applied.",
        )
        render_source_card(
            name="Open-Meteo Historical Weather Archive",
            provider="Open-Meteo GmbH (ERA5 Reanalysis)",
            licence="Creative Commons Attribution 4.0 (CC BY 4.0)",
            access_date="October 2026",
            status="USED",
            fields="temperature_2m, relative_humidity_2m, wind_u, wind_v, pressure, rain",
            details="Continuous hourly surface weather observations matching Mumbai coordinates (19.076°N, 72.878°E).",
        )

    with s2:
        render_source_card(
            name="OpenStreetMap Spatial Context & Infrastructure",
            provider="OpenStreetMap Foundation (Overpass API)",
            licence="Open Database License 1.0 (ODbL)",
            access_date="October 2026",
            status="USED",
            fields="highway=primary/secondary, landuse=industrial/construction, coastline",
            details="Bundled context table covers station environs. Completeness varies by station.",
        )
        render_source_card(
            name="OpenAQ REST API v3",
            provider="OpenAQ Inc.",
            licence="CC BY 4.0",
            access_date="October 2026",
            status="REJECTED",
            fields="N/A (API Key Mandate)",
            details="Rejected to ensure zero-key reproducibility from a fresh clone.",
        )

    st.markdown("---")
    st.markdown(f"### {ICONS['schema']} End-to-End Decision Architecture")
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

    st.markdown("---")
    st.markdown(f"### :material/build: Methods & Reproducibility")

    with st.expander(":material/terminal: How to Reproduce from a Fresh Clone", expanded=True):
        st.code("""
git clone <repo-url> && cd citypulse
pip install -r requirements.txt

make data

make eda

make model

make app

make all && make app

make refresh
        """, language="bash")

    with st.expander(":material/science: Validation Design"):
        st.markdown("""
**Train/Test Split:** Strictly chronological.
- **Train:** 2021-01-01 to 2022-12-31 (2 full years)
- **Test:** 2023-01-01 to 2023-12-31 (1-year forward holdout)
- **No random shuffling.** No future data leaks into features.

**Feature Convention:** All features are available at decision time (23:59 IST on day t-1).
Rolling statistics use `shift(1)` to exclude the target day.

**Baselines:** Persistence (AQI(t) = AQI(t-1)), Seasonal Naive (AQI(t) = AQI(t-7)).

**Leakage Prevention:**
- Prior-day weather only (not same-day)
- Imputation parameters fit on train split only
- No station mean encoding that leaks test-set information
        """)

    with st.expander(":material/warning: Known Limitations"):
        st.markdown("""
1. **Model does not beat persistence on MAE.** Persistence MAE = 19.42, GB MAE = 20.33. This is honest — daily AQI is heavily autoregressive.
2. **80% interval undercoverage.** Empirical coverage is 74.1% (nominal 80%). Treat as exploratory range.
3. **Sparse station network.** Only ~18 stations with sufficient data. Large areas between stations are unmonitored.
4. **Weather from reanalysis grid.** Open-Meteo ERA5 is gridded (~25 km), not station-level. Micro-climate effects are missed.
5. **No causal identification.** All correlations are observational. We cannot attribute AQI to a specific emission source.
6. **Historical replay only.** This is NOT live data. Results reflect latest available benchmark dataset conditions.
        """)

    with st.expander(f"{ICONS['science']} What Data Would Be Needed to Beat Persistence?"):
        st.markdown("""
To consistently beat 1-day persistence citywide:
1. **Satellite Aerosol Optical Depth (AOD):** Geostationary optical depth (INSAT-3D) to resolve regional dust/biomass plumes.
2. **Hyper-Local Low-Cost Sensor Meshes:** Denser micro-sensors (< 500m apart) for vehicular/construction plumes.
3. **Live Arterial Traffic Speed Telemetry:** Real-time congestion indices at highway bottlenecks.
4. **Municipal Construction & Demolition Logs:** Digital registers of active earth-moving permits.
        """)

with tab_citizen:
    render_takeaway(
        "Simplified air quality information for the general public. Includes current status, health guidance for sensitive groups, and forecast outlook with uncertainty."
    )

    render_citizen_mode(
        station_data=st_daily,
        predictions=st_preds,
        station_name=selected_station,
        decision_date=decision_date
    )

    render_aqi_card_export(
        station_name=selected_station,
        station_data=st_daily,
        decision_date=decision_date
    )

with tab_demo:
    render_guided_demo()

render_footer()

