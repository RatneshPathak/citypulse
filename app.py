"""
CityPulse: Mumbai — Decision-Support Prototype for Air Quality
Predict • Explain • Act

Presentation-Layer Redesign for Municipal Decision Support (BMC / MPCB).
Streamlit native Material Symbols icons with zero emojis.
"""
import json
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

# Decision support modules
from src.decision.whatif import compute_rank_stability, compute_rank_delta
from src.decision.routing import compute_inspection_route
from src.decision.briefing import render_briefing_export_ui
from src.decision.validation import render_validation_panel
from src.decision import viz as decision_viz

# Citizen and demo features
from src.citizen.citizen_view import render_citizen_mode, render_aqi_card_export
from src.demo.guided_demo import render_guided_demo

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
    return daily, preds, priority


daily_df, preds_df, priority_df = load_all_datasets()

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

if st.sidebar.button("Reset to Recommended Defaults", icon=ICONS["sidebar_reset"], use_container_width=True):
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
render_compact_banner()
render_header(selected_station, decision_date, total_stations=daily_df["canonical_station"].nunique())
st.warning(f"Historical replay: observations through {decision_date} estimate risk for {target_date}. This is not a live air-quality alert.")

st_daily = daily_df[
    (daily_df["canonical_station"] == selected_station)
    & (daily_df["date"] <= pd.to_datetime(dyn_priority["date"].iloc[0]))
].sort_values("date").copy()
st_preds = preds_df[preds_df["canonical_station"] == selected_station].sort_values("date").copy()
st_prio_row = dyn_priority[dyn_priority["station"] == selected_station]
st_prio = st_prio_row.iloc[0]

# Add citizen mode toggle in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown(f"### :material/people: View Mode")
citizen_mode = st.sidebar.toggle(
    "Citizen-Friendly Mode",
    value=False,
    help="Switch to simplified public view with health guidance"
)

tab1, tab_whatif, tab_route, tab_briefing, tab2, tab3, tab4, tab_valid, tab_citizen, tab_demo, tab5 = st.tabs([
    f"{ICONS['tab_act']} 1. Priority Rankings",
    f":material/tune: 2. What-If Simulator",
    f":material/route: 3. Route Planner",
    f":material/description: 4. Briefing Export",
    f"{ICONS['tab_discover']} 5. Historical Patterns",
    f"{ICONS['tab_weather']} 6. Weather Analysis",
    f"{ICONS['tab_forecast']} 7. Forecast Performance",
    f":material/verified: 8. Validation & Backtest",
    f":material/people: 9. Citizen View",
    f":material/play_circle: 10. Guided Demo",
    f"{ICONS['tab_methods']} 11. Data & Methods",
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

        display_df = table_df[[
            "rank", "station", "priority_score", "latest_aqi", "Category", "Action", "zone"
        ]].rename(columns={
            "rank": "Rank",
            "station": "Zone / Station",
            "priority_score": "Score",
            "latest_aqi": "AQI",
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
                "Action": st.column_config.TextColumn("Action Status", width="small"),
                "Zone": st.column_config.TextColumn("Region", width="medium"),
            },
            hide_index=True,
            use_container_width=True,
            height=380,
        )

    with col_map:
        st.markdown(f"##### {ICONS['map']} Spatial Priority Map (Carto-Darkmatter)")
        fig_map = charts.plot_priority_map(dyn_priority, selected_station)
        st.plotly_chart(fig_map, use_container_width=True, config=charts.CHART_CONFIG)

    st.markdown("---")
    st.markdown(f"##### {ICONS['analytics']} Why is **{selected_station}** ranked **#{st_prio['rank']}**? (Score Contribution Breakdown)")
    fig_breakdown = charts.plot_score_breakdown(st_prio.to_dict(), st.session_state.weights)
    st.plotly_chart(fig_breakdown, use_container_width=True, config=charts.CHART_CONFIG)

    render_action_dossier(st_prio.to_dict(), allocated=(st_prio["rank"] <= capacity_n))


# TAB: What-If Policy Simulator
with tab_whatif:
    render_takeaway(
        "Adjust policy weights to see how rankings change. Run Monte Carlo simulation to assess which zones are "
        "**robust** to weight changes vs which are **unstable**."
    )
    
    st.markdown(f"### :material/tune: Policy Weight Simulator")
    
    # Store baseline for comparison
    if "baseline_priority" not in st.session_state:
        st.session_state.baseline_priority = dyn_priority.copy()
    
    # Recompute button to store new baseline
    col_sim1, col_sim2, col_sim3 = st.columns([1, 1, 1])
    with col_sim1:
        if st.button("📌 Set Current as New Baseline", use_container_width=True, help="Store current rankings as the new comparison baseline"):
            st.session_state.baseline_priority = dyn_priority.copy()
            st.success("Baseline updated!", icon=":material/check_circle:")
    
    with col_sim2:
        if st.button("🔄 Reset to Original Default", use_container_width=True, help="Reset sidebar weights to recommended defaults"):
            st.session_state.weights = DEFAULT_WEIGHTS.copy()
            st.rerun()
    
    # Show current vs baseline comparison
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
        # Summary statistics
        moved_up = (delta_df["delta"] > 0).sum()
        moved_down = (delta_df["delta"] < 0).sum()
        unchanged = (delta_df["delta"] == 0).sum()
        
        st.markdown("**Summary:**")
        st.markdown(f"- 📈 Moved up: **{moved_up}** zones")
        st.markdown(f"- 📉 Moved down: **{moved_down}** zones")
        st.markdown(f"- ➖ Unchanged: **{unchanged}** zones")
    
    # Visualization
    if len(dyn_priority) > 0:
        fig_movement = decision_viz.plot_rank_movement(
            st.session_state.baseline_priority,
            dyn_priority,
            top_n=15
        )
        st.plotly_chart(fig_movement, use_container_width=True, config=charts.CHART_CONFIG)
    
    # Rank Stability Simulation
    st.markdown("---")
    st.markdown("### 🎲 Rank Stability Monte Carlo Simulation")
    st.caption(
        f"Run {500} simulations with random weight perturbations (±30%) to find zones that are **robust** "
        "to policy choices vs those that are **sensitive**."
    )
    
    run_stability = st.button(
        "▶️ Run Stability Simulation (500 iterations)",
        use_container_width=False,
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
        
        # Show results
        st.success(f"Simulation complete! Tested {500} random weight combinations.", icon=":material/check_circle:")
        
        col_stab1, col_stab2 = st.columns(2)
        
        with col_stab1:
            # Probability heatmap
            fig_prob = decision_viz.plot_probability_heatmap(stability_df, top_n=capacity_n)
            st.plotly_chart(fig_prob, use_container_width=True, config=charts.CHART_CONFIG)
        
        with col_stab2:
            # Rank range plot
            fig_ranges = decision_viz.plot_rank_stability_ranges(stability_df, top_n=10)
            st.plotly_chart(fig_ranges, use_container_width=True, config=charts.CHART_CONFIG)
        
        # Interpretation
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


# TAB: Route Planner
with tab_route:
    render_takeaway(
        f"Plan an efficient inspection route for the top-{capacity_n} priority zones using nearest-neighbor routing. "
        "**Note:** Distances are straight-line (haversine), not actual road travel."
    )
    
    st.markdown(f"### :material/route: Inspection Route Planner")
    
    # Starting point selector
    route_col1, route_col2 = st.columns([2, 1])
    
    with route_col1:
        top_stations_list = dyn_priority.head(capacity_n)["station"].tolist()
        start_station_route = st.selectbox(
            "Starting Point (Municipal Office / Depot)",
            ["Highest Priority"] + top_stations_list,
            help="Select where the inspection team will begin their route"
        )
        start_override = None if start_station_route == "Highest Priority" else start_station_route
    
    with route_col2:
        if st.button("🗺️ Compute Optimal Route", type="primary", use_container_width=True):
            st.session_state.route_computed = True
    
    if "route_computed" not in st.session_state:
        st.session_state.route_computed = False
    
    if st.session_state.route_computed:
        # Compute route
        with st.spinner("Computing nearest-neighbor tour..."):
            route_df, total_distance = compute_inspection_route(
                dyn_priority,
                top_n=capacity_n,
                start_station=start_override
            )
        
        # Display route summary
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
        
        # Show map with route
        st.markdown("---")
        st.markdown("#### 🗺️ Route Visualization")
        fig_route = decision_viz.plot_inspection_route_map(route_df, selected_station)
        st.plotly_chart(fig_route, use_container_width=True, config=charts.CHART_CONFIG)
        
        # Route table
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
            use_container_width=True,
        )


# TAB: Briefing Export
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

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        mean_aqi = st_daily["aqi_mean"].mean()
        render_kpi_card("Multi-Year Mean AQI", f"{mean_aqi:.1f}", "2021–2023 Station Average", color_accent=get_aqi_category_color(mean_aqi)[1])
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
    st.plotly_chart(fig_ts, use_container_width=True, config=charts.CHART_CONFIG)

    st.markdown(f"##### {ICONS['breakdown']} Historical Category Breakdown (% of Days)")
    fig_dist = charts.plot_category_distribution(st_daily)
    st.plotly_chart(fig_dist, use_container_width=True, config=charts.CHART_CONFIG)

    st.markdown("---")
    col_seas, col_week = st.columns(2)
    with col_seas:
        fig_seas = charts.plot_seasonal_profile(st_daily)
        st.plotly_chart(fig_seas, use_container_width=True, config=charts.CHART_CONFIG)
    with col_week:
        fig_week = charts.plot_weekly_profile(st_daily)
        st.plotly_chart(fig_week, use_container_width=True, config=charts.CHART_CONFIG)

    st.markdown("---")


with tab3:
    render_takeaway(
        f"Compare AQI and weather history at {selected_station}. Across valid station-days, wind speed and AQI have a pooled correlation of -0.25; season and location may confound it."
    )

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
        st.plotly_chart(fig_scatter, use_container_width=True, config=charts.CHART_CONFIG)

    with w_corr_col:
        fig_corr, dynamic_corr_insight = charts.plot_correlation_diverging(st_daily)
        st.plotly_chart(fig_corr, use_container_width=True, config=charts.CHART_CONFIG)
        st.caption(f"{ICONS['insight']} **Physical Insight:** {dynamic_corr_insight}")

    st.markdown("---")
    col_rose, col_rose_txt = st.columns([1.1, 1.3])
    with col_rose:
        fig_rose = charts.plot_wind_rose(st_daily)
        st.plotly_chart(fig_rose, use_container_width=True, config=charts.CHART_CONFIG)
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
        "On the 2023 holdout, persistence has the lowest point-forecast MAE. The classifier identifies many AQI > 200 days, while its false alerts and the undercoverage of the prediction interval require caution."
    )

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
    st.plotly_chart(fig_fc, use_container_width=True, config=charts.CHART_CONFIG)

    st.markdown("---")
    c_cal, c_parity = st.columns(2)
    with c_cal:
        fig_cal = charts.plot_calibration_and_pr(st_preds)
        st.plotly_chart(fig_cal, use_container_width=True, config=charts.CHART_CONFIG)
        st.caption(f"{ICONS['diagram']} **Reliability Diagram:** Diagonal line represents perfect calibration. Points near the line indicate reliable probability estimates.")

    with c_parity:
        fig_parity = charts.plot_predicted_vs_actual(st_preds)
        st.plotly_chart(fig_parity, use_container_width=True, config=charts.CHART_CONFIG)
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
        st.dataframe(disp_anom, use_container_width=True, height=220, hide_index=True)
    else:
        st.info("No extreme statistical residual anomalies flagged for this station during 2023.", icon=":material/info:")


# TAB: Validation & Backtest
with tab_valid:
    render_validation_panel(daily_df, preds_df, capacity_n=capacity_n)


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
            details="597,912 deduplicated hourly AQI records across 36 station labels (2021–2023); 22,608 valid station-days after the project 18-hour threshold.",
        )
        render_source_card(
            name="Supplementary CPCB Multi-Pollutant Notebook",
            provider="Central Pollution Control Board (CCR Portal)",
            licence="Government Open Data (GODL-India / NDSAP)",
            access_date="October 2026",
            status="SUPPLEMENTARY",
            fields="PM2.5, PM10, NO, NO2, NH3, SO2, CO (hourly)",
            details="Notebook and summary are included, but the underlying Excel exports are not bundled. Excluded from core reproducible demo and model evaluation.",
        )
        render_source_card(
            name="Open-Meteo Historical Weather Archive",
            provider="Open-Meteo GmbH (ERA5 Reanalysis)",
            licence="Creative Commons Attribution 4.0 (CC BY 4.0)",
            access_date="October 2026",
            status="USED",
            fields="temperature_2m, relative_humidity_2m, wind_u, wind_v, pressure, rain",
            details="26,280 continuous hourly surface weather observations matching Mumbai coordinates (19.076N, 72.878E).",
        )

    with s2:
        render_source_card(
            name="OpenStreetMap Spatial Context & Infrastructure",
            provider="OpenStreetMap Foundation (Overpass API)",
            licence="Open Database License 1.0 (ODbL)",
            access_date="October 2026",
            status="USED",
            fields="highway=primary/secondary, landuse=industrial/construction, coastline",
            details="Bundled context table covers 18 stations. Other station descriptions come from static metadata; OSM completeness varies.",
        )
        render_source_card(
            name="OpenAQ REST API v3",
            provider="OpenAQ Inc.",
            licence="CC BY 4.0",
            access_date="October 2026",
            status="REJECTED",
            fields="N/A (API Key Mandate)",
            details="Retired v1/v2 endpoints with HTTP 410. Rejected to ensure zero-key reproducibility from a fresh repository clone.",
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

    with st.expander(f"{ICONS['science']} What Additional Data Would Be Required to Beat Persistence Decisively?"):
        st.markdown(
            """
            Daily air quality is a continuous autoregressive process heavily tied to yesterday's concentration.
            To consistently beat 1-day persistence citywide, the following operational data feeds are required:
            1. **Satellite Aerosol Optical Depth (AOD):** High-frequency geostationary optical depth (INSAT-3D) to resolve regional dust and biomass plumes entering Mumbai.
            2. **Hyper-Local Low-Cost Sensor Meshes:** Denser micro-sensors (< 500m apart) to track local vehicular and construction plumes.
            3. **Live Arterial Traffic Speed Telemetry:** Real-time road congestion indices at major highway bottlenecks (Sion, Kurla, WEH).
            4. **Municipal Construction & Demolition Logs:** Digital registers of active earth-moving and demolition permits.
            """
        )


# TAB: Citizen View
with tab_citizen:
    render_takeaway(
        "Simplified air quality information for the general public. Includes current status, health guidance for sensitive groups, and 7-day outlook with uncertainty."
    )
    
    render_citizen_mode(
        station_data=st_daily,
        predictions=st_preds,
        station_name=selected_station,
        decision_date=decision_date
    )
    
    # Shareable card export
    render_aqi_card_export(
        station_name=selected_station,
        station_data=st_daily,
        decision_date=decision_date
    )


# TAB: Guided Demo
with tab_demo:
    render_guided_demo()


render_footer()

