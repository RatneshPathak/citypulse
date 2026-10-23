"""
CityPulse: Mumbai — Chart Generation Engine
Dedicated functions for all Plotly data visualizations using the CityPulse design system.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.calibration import calibration_curve
from sklearn.metrics import precision_recall_curve, average_precision_score

from theme import COLORS, AQI_PALETTE, AQI_BREAKPOINTS, get_aqi_category_color
from src.eda.visualizations import (
    plot_station_comparison,
    plot_monthly_trends,
    plot_diurnal_cycle,
    plot_distribution_boxplots,
    plot_outlier_summary,
)

CHART_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
        "hoverClosestCartesian",
        "hoverCompareCartesian",
    ],
}

def plot_priority_map(priority_df: pd.DataFrame, selected_station: str) -> go.Figure:
    """
    Renders the dark interactive map with:
    - Dark basemap (carto-darkmatter, token-free)
    - Marker size = latest AQI, color = priority score (YlOrRd)
    - Selected station highlighted with an accent ring
    - Only top-5 stations labeled directly
    """
    df = priority_df.dropna(subset=["latitude", "longitude"]).copy()

    df["aqi_cat"] = df["latest_aqi"].apply(lambda v: get_aqi_category_color(v)[0])
    df["label_text"] = np.where(df["rank"] <= 5, df["rank"].astype(str) + ". " + df["station"], "")

    use_modern_map = hasattr(go, "Scattermap")
    scatter_cls = go.Scattermap if use_modern_map else go.Scattermapbox

    fig = go.Figure()

    fig.add_trace(
        scatter_cls(
            lat=df["latitude"],
            lon=df["longitude"],
            mode="markers+text",
            marker=dict(
                size=np.clip(df["latest_aqi"] / 8.0, 10, 32),
                color=df["priority_score"],
                colorscale="YlOrRd",
                showscale=True,
                colorbar=dict(
                    title=dict(text="Priority Score", font=dict(color=COLORS["text"], size=11)),
                    tickfont=dict(color=COLORS["text_muted"], size=10),
                    len=0.75,
                    thickness=12,
                    outlinewidth=0,
                ),
                opacity=0.88,
            ),
            text=df["label_text"],
            textposition="top right",
            textfont=dict(family="Inter, sans-serif", size=11, color="#ffffff"),
            customdata=np.stack(
                (
                    df["station"],
                    df["rank"],
                    df["priority_score"],
                    df["latest_aqi"],
                    df["aqi_cat"],
                    df["zone"],
                ),
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Rank: <b>#%{customdata[1]}</b> • Priority Score: <b>%{customdata[2]:.1f}</b><br>"
                "Latest AQI: <b>%{customdata[3]:.0f}</b> (%{customdata[4]})<br>"
                "Zone: %{customdata[5]}"
                "<extra></extra>"
            ),
            name="Stations",
        )
    )

    sel_df = df[df["station"] == selected_station]
    if not sel_df.empty:
        fig.add_trace(
            scatter_cls(
                lat=sel_df["latitude"],
                lon=sel_df["longitude"],
                mode="markers",
                marker=dict(
                    size=np.clip(sel_df["latest_aqi"].iloc[0] / 8.0, 10, 32) + 12,
                    color="rgba(0, 210, 255, 0.2)",
                    opacity=1.0,
                ),
                hoverinfo="none",
                showlegend=False,
            )
        )
        fig.add_trace(
            scatter_cls(
                lat=sel_df["latitude"],
                lon=sel_df["longitude"],
                mode="markers",
                marker=dict(
                    size=np.clip(sel_df["latest_aqi"].iloc[0] / 8.0, 10, 32) + 4,
                    color="#00D2FF",
                    opacity=1.0,
                ),
                hoverinfo="none",
                showlegend=False,
            )
        )

    center_lat = df["latitude"].mean() if not df.empty else 19.0760
    center_lon = df["longitude"].mean() if not df.empty else 72.8777

    map_config = dict(
        style="carto-darkmatter",
        center=dict(lat=center_lat, lon=center_lon),
        zoom=9.8,
    )

    if use_modern_map:
        fig.update_layout(map=map_config, margin=dict(l=0, r=0, t=10, b=0), height=420)
    else:
        fig.update_layout(mapbox=map_config, margin=dict(l=0, r=0, t=10, b=0), height=420)

    return fig

def plot_score_breakdown(st_data: dict, weights: dict) -> go.Figure:
    """
    Renders a horizontal stacked bar showing why the selected station received its score.
    """
    total_w = sum(weights.values()) or 1.0

    components = [
        ("Exposure (7-day)", st_data.get("score_exposure", 0), weights["w_exp"] / total_w, "#E5484D"),
        ("Persistence (>150)", st_data.get("score_persistence", 0), weights["w_pers"] / total_w, "#F08A3C"),
        ("Trend Acceleration", st_data.get("score_trend", 0), weights["w_trend"] / total_w, "#F5C542"),
        ("Forecast Risk", st_data.get("score_forecast", 0), weights["w_fore"] / total_w, "#4F8CFF"),
        ("Vulnerability/Gap", st_data.get("score_vulnerability", 0), weights["w_gap"] / total_w, "#9D7BFF"),
    ]

    fig = go.Figure()
    for name, raw_score, norm_w, col in components:
        weighted_contrib = raw_score * norm_w
        fig.add_trace(
            go.Bar(
                y=["Score Composition"],
                x=[weighted_contrib],
                name=name,
                orientation="h",
                marker=dict(color=col),
                hovertemplate=f"<b>{name}</b><br>Raw Sub-Score: {raw_score:.1f}/100<br>Weight: {norm_w*100:.0f}%<br>Points Added: <b>+{weighted_contrib:.1f}</b><extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        height=110,
        margin=dict(l=10, r=10, t=10, b=25),
        xaxis=dict(
            title=dict(text="Total Priority Score Points", font=dict(size=11, color=COLORS["text_muted"])),
            range=[0, 100],
            showgrid=True,
        ),
        yaxis=dict(showticklabels=False),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
        ),
    )
    return fig

def plot_timeseries_trajectory(
    st_daily: pd.DataFrame,
    selected_station: str,
    show_season_shading: bool = True,
) -> go.Figure:
    """
    Renders the longitudinal AQI series with:
    - Subtle CPCB category background shading with labels pinned to the right edge
    - Thin daily actual line + thicker 7-day rolling trend
    - Range slider + quick-range buttons (1M, 6M, 1Y, All)
    - Honest gaps (connectgaps=False)
    - Annotations on peak historical episodes
    """
    df = st_daily.sort_values("date").copy()
    df["rolling_7"] = df["aqi_mean"].rolling(7, min_periods=3).mean()

    fig = go.Figure()

    for low, high, cat, col in AQI_BREAKPOINTS:
        y_max = min(high, 450)
        fig.add_hrect(
            y0=low,
            y1=y_max,
            fillcolor=col,
            opacity=0.07,
            layer="below",
            line_width=0,
            annotation_text=f"{cat} ({low}-{high})",
            annotation_position="top right",
            annotation_font=dict(size=10, color=col),
        )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["aqi_mean"],
            mode="lines",
            name="Daily Mean AQI",
            line=dict(color="rgba(230, 237, 247, 0.45)", width=1.2),
            connectgaps=False,
            hovertemplate="Date: <b>%{x|%d %b %Y}</b><br>AQI: <b>%{y:.0f}</b><extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["rolling_7"],
            mode="lines",
            name="7-Day Rolling Trend",
            line=dict(color=COLORS["accent"], width=2.8),
            connectgaps=False,
            hovertemplate="Date: <b>%{x|%d %b %Y}</b><br>7-Day Trend: <b>%{y:.1f} AQI</b><extra></extra>",
        )
    )

    if not df.empty and df["aqi_mean"].notna().any():
        peak_row = df.loc[df["aqi_mean"].idxmax()]
        fig.add_annotation(
            x=peak_row["date"],
            y=peak_row["aqi_mean"],
            text=f"Peak: {peak_row['aqi_mean']:.0f} AQI",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowcolor="#E5484D",
            font=dict(color="#ffffff", size=10, family="Inter"),
            bgcolor="rgba(229, 72, 77, 0.8)",
            bordercolor="#E5484D",
            borderwidth=1,
            borderpad=4,
        )

    rangeselector = dict(
        buttons=list(
            [
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(step="all", label="All Data"),
            ]
        ),
        bgcolor=COLORS["surface_raised"],
        activecolor=COLORS["accent"],
        font=dict(color=COLORS["text"], size=10),
    )

    fig.update_layout(
        title=f"Air Quality Trajectory at {selected_station} (2021–2023)",
        xaxis=dict(
            title="",
            rangeselector=rangeselector,
            rangeslider=dict(visible=True, thickness=0.06, bgcolor=COLORS["surface"]),
            type="date",
        ),
        yaxis=dict(title="Daily Mean AQI", range=[0, max(350, df["aqi_mean"].max() + 20)]),
        hovermode="x unified",
        height=440,
        margin=dict(l=45, r=85, t=45, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    )
    return fig

def plot_category_distribution(st_daily: pd.DataFrame) -> go.Figure:
    """
    Renders a 100% horizontal stacked distribution strip showing % of days in each CPCB category.
    """
    valid_df = st_daily.dropna(subset=["aqi_mean"]).copy()
    if valid_df.empty:
        return go.Figure()

    valid_df["cat"] = valid_df["aqi_mean"].apply(lambda v: get_aqi_category_color(v)[0])
    counts = valid_df["cat"].value_counts(normalize=True) * 100

    fig = go.Figure()
    order = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
    for cat in order:
        pct = counts.get(cat, 0.0)
        if pct > 0:
            fig.add_trace(
                go.Bar(
                    y=["Days Distribution"],
                    x=[pct],
                    name=cat,
                    orientation="h",
                    marker=dict(color=AQI_PALETTE[cat]),
                    hovertemplate=f"<b>{cat}</b>: {pct:.1f}% of days<extra></extra>",
                )
            )

    fig.update_layout(
        barmode="stack",
        height=90,
        margin=dict(l=10, r=10, t=10, b=20),
        xaxis=dict(
            title=dict(text="Percentage of Monitoring Days (%)", font=dict(size=10, color=COLORS["text_muted"])),
            range=[0, 100],
            showgrid=False,
        ),
        yaxis=dict(showticklabels=False),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
        ),
    )
    return fig

def plot_seasonal_profile(st_daily: pd.DataFrame) -> go.Figure:
    """Renders the monthly seasonality bar profile."""
    df = st_daily.dropna(subset=["aqi_mean"]).copy()
    df["month_num"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")

    m_agg = (
        df.groupby(["month_num", "month_name"])["aqi_mean"]
        .mean()
        .reset_index()
        .sort_values("month_num")
    )
    m_agg["cat_color"] = m_agg["aqi_mean"].apply(lambda v: get_aqi_category_color(v)[1])

    fig = go.Figure(
        go.Bar(
            x=m_agg["month_name"],
            y=m_agg["aqi_mean"],
            marker=dict(color=m_agg["cat_color"]),
            hovertemplate="<b>%{x}</b>: Mean AQI <b>%{y:.1f}</b><extra></extra>",
        )
    )

    fig.add_vrect(
        x0="Jun",
        x1="Sep",
        fillcolor="rgba(0, 210, 255, 0.08)",
        layer="below",
        line_width=1,
        line_dash="dot",
        line_color="rgba(0, 210, 255, 0.3)",
        annotation_text="Monsoon Washout",
        annotation_position="top left",
        annotation_font=dict(size=10, color="#00D2FF"),
    )

    fig.update_layout(
        title="Monthly Seasonal Profile (Monsoon Washout vs Winter Inversion)",
        yaxis=dict(title="Mean Daily AQI"),
        xaxis=dict(title=""),
        height=300,
        margin=dict(l=40, r=20, t=40, b=20),
    )
    return fig

def plot_weekly_profile(st_daily: pd.DataFrame) -> go.Figure:
    """Renders the day-of-week profile."""
    df = st_daily.dropna(subset=["aqi_mean"]).copy()
    df["day_num"] = df["date"].dt.day_of_week
    df["day_name"] = df["date"].dt.strftime("%a")

    w_agg = (
        df.groupby(["day_num", "day_name"])["aqi_mean"]
        .mean()
        .reset_index()
        .sort_values("day_num")
    )
    colors = [COLORS["accent"] if d < 5 else "rgba(79, 140, 255, 0.45)" for d in w_agg["day_num"]]

    fig = go.Figure(
        go.Bar(
            x=w_agg["day_name"],
            y=w_agg["aqi_mean"],
            marker=dict(color=colors),
            hovertemplate="<b>%{x}</b>: Mean AQI <b>%{y:.1f}</b><extra></extra>",
        )
    )
    fig.update_layout(
        title="Day-of-Week Rhythm (Weekday Commute vs Weekend Respite)",
        yaxis=dict(title="Mean Daily AQI"),
        xaxis=dict(title=""),
        height=300,
        margin=dict(l=40, r=20, t=40, b=20),
    )
    return fig

def plot_weather_scatter(st_daily: pd.DataFrame) -> go.Figure:
    """
    Renders wind speed vs AQI scatter:
    - Ordered CPCB category legend (Good to Severe)
    - Shaded stagnant wind zone (<6 km/h)
    - Binned median trendline
    - Opacity 0.6, marker size 6
    """
    df = st_daily.dropna(subset=["aqi_mean", "wind_speed_mean"]).copy()
    df["cat"] = df["aqi_mean"].apply(lambda v: get_aqi_category_color(v)[0])

    fig = go.Figure()

    fig.add_vrect(
        x0=0,
        x1=6.0,
        fillcolor="rgba(229, 72, 77, 0.08)",
        layer="below",
        line_width=1,
        line_dash="dot",
        line_color="rgba(229, 72, 77, 0.4)",
        annotation_text="Stagnant Air (<6 km/h)",
        annotation_position="top right",
        annotation_font=dict(size=10, color="#E5484D"),
    )

    order = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
    for cat in order:
        sub = df[df["cat"] == cat]
        if not sub.empty:
            fig.add_trace(
                go.Scatter(
                    x=sub["wind_speed_mean"],
                    y=sub["aqi_mean"],
                    mode="markers",
                    name=cat,
                    marker=dict(
                        color=AQI_PALETTE[cat],
                        size=6,
                        opacity=0.6,
                        line=dict(width=0.5, color="#000000"),
                    ),
                    hovertemplate=(
                        f"Category: <b>{cat}</b><br>"
                        "Wind Speed: <b>%{x:.1f} km/h</b><br>"
                        "AQI: <b>%{y:.0f}</b><extra></extra>"
                    ),
                )
            )

    df["wind_bin"] = pd.cut(df["wind_speed_mean"], bins=np.linspace(0, 30, 15))
    binned = df.groupby("wind_bin", observed=True).agg(
        wind=("wind_speed_mean", "median"),
        aqi=("aqi_mean", "median"),
    ).dropna()

    fig.add_trace(
        go.Scatter(
            x=binned["wind"],
            y=binned["aqi"],
            mode="lines",
            name="Binned Median Trend",
            line=dict(color="#ffffff", width=2.5, dash="dash"),
            hoverinfo="none",
        )
    )

    fig.update_layout(
        title="Ventilation Mechanics: Surface Wind Speed vs Daily AQI",
        xaxis=dict(title="Daily Mean Wind Speed (km/h)"),
        yaxis=dict(title="Daily AQI"),
        height=380,
        margin=dict(l=45, r=20, t=45, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    )
    return fig

def plot_correlation_diverging(st_daily: pd.DataFrame) -> tuple[go.Figure, str]:
    """
    Renders a diverging horizontal bar chart of meteorological correlations with AQI.
    Returns (fig, insight_text).
    """
    df = st_daily.dropna(subset=["aqi_mean"]).copy()
    candidate_cols = {
        "wind_speed_mean": "Wind Speed (10m)",
        "wind_u_mean": "Sea-Breeze Vector (u)",
        "temp_mean": "Surface Temperature",
        "humidity_mean": "Relative Humidity",
        "rain_total_mm": "Precipitation / Rain",
        "pressure_mean": "Surface Atmospheric Pressure",
    }
    available = [c for c in candidate_cols if c in df.columns]
    corr_series = df[available + ["aqi_mean"]].corr()["aqi_mean"].drop("aqi_mean")

    corr_df = pd.DataFrame({
        "var_raw": corr_series.index,
        "var_name": [candidate_cols[c] for c in corr_series.index],
        "r": corr_series.values,
        "abs_r": np.abs(corr_series.values),
    }).sort_values("abs_r", ascending=True)

    colors = [COLORS["accent"] if val < 0 else "#E5484D" for val in corr_df["r"]]

    fig = go.Figure(
        go.Bar(
            y=corr_df["var_name"],
            x=corr_df["r"],
            orientation="h",
            marker=dict(color=colors),
            hovertemplate="<b>%{y}</b>: Pearson r = <b>%{x:.2f}</b><extra></extra>",
            text=[f"{v:+.2f}" for v in corr_df["r"]],
            textposition="auto",
            textfont=dict(color="#ffffff", size=11, family="Inter"),
        )
    )

    fig.add_vline(x=0, line_width=1, line_color=COLORS["border"])

    fig.update_layout(
        title="Meteorological Correlations with AQI (Diverging r)",
        xaxis=dict(title="Pearson Correlation Coefficient (r)", range=[-0.8, 0.8]),
        yaxis=dict(title=""),
        height=320,
        margin=dict(l=150, r=30, t=40, b=30),
    )

    top_var = corr_df.iloc[-1]
    strength = "strong" if top_var["abs_r"] >= 0.50 else ("moderate" if top_var["abs_r"] >= 0.30 else "weak")
    direction = "cleansing / dispersive" if top_var["r"] < 0 else "trapping / stagnation"
    insight_text = (
        f"The primary meteorological driver at this station is **{top_var['var_name']}** "
        f"with a **{strength}** correlation of **r = {top_var['r']:.2f}**, acting as a dominant **{direction}** factor."
    )

    return fig, insight_text

def plot_wind_rose(st_daily: pd.DataFrame) -> go.Figure:
    """Renders a polar bar chart showing mean AQI by 8 wind direction octants."""
    df = st_daily.dropna(subset=["aqi_mean", "wind_u_mean", "wind_v_mean"]).copy()
    if df.empty:
        return go.Figure()

    wind_dir = (180.0 + (180.0 / np.pi) * np.arctan2(df["wind_u_mean"], df["wind_v_mean"])) % 360.0
    df["dir_bin"] = pd.cut(
        wind_dir,
        bins=[0, 45, 90, 135, 180, 225, 270, 315, 360],
        labels=["N", "NE", "E", "SE", "S", "SW (Maritime)", "W (Maritime)", "NW"],
        right=False,
    )

    rose_agg = df.groupby("dir_bin", observed=True)["aqi_mean"].mean().reset_index()
    rose_agg["cat_color"] = rose_agg["aqi_mean"].apply(lambda v: get_aqi_category_color(v)[1])

    fig = go.Figure(
        go.Barpolar(
            r=rose_agg["aqi_mean"],
            theta=rose_agg["dir_bin"],
            marker=dict(color=rose_agg["cat_color"], line=dict(color=COLORS["border"], width=1)),
            hovertemplate="Direction: <b>%{theta}</b><br>Mean AQI: <b>%{r:.1f}</b><extra></extra>",
        )
    )

    fig.update_layout(
        title="Wind Direction vs Air Quality (Polar Octants)",
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(200, rose_agg['aqi_mean'].max() + 20)], gridcolor="rgba(143, 161, 189, 0.1)"),
            angularaxis=dict(gridcolor="rgba(143, 161, 189, 0.1)"),
            bgcolor=COLORS["surface"],
        ),
        height=320,
        margin=dict(l=30, r=30, t=45, b=25),
    )
    return fig

def plot_holdout_forecast(st_preds: pd.DataFrame, selected_station: str) -> go.Figure:
    """
    Renders the 2023 forward holdout forecast:
    - Actual as solid light line
    - Forecast as dashed accent line
    - 80% interval as smooth translucent band (fill='toself')
    - Threshold line at 200 labelled directly on the line
    - Red markers on days where actual exceeded the threshold
    - Range slider
    """
    df = st_preds.sort_values("date").copy()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=pd.concat([df["date"], df["date"][::-1]]),
            y=pd.concat([df["pred_p90"], df["pred_p10"][::-1]]),
            fill="toself",
            fillcolor="rgba(79, 140, 255, 0.16)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="none",
            showlegend=True,
            name="80% Prediction Interval [p10–p90]",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["target_next_day_aqi"],
            mode="lines",
            name="Actual Ground Truth",
            line=dict(color="#ffffff", width=1.8),
            hovertemplate="Date: <b>%{x|%d %b %Y}</b><br>Actual AQI: <b>%{y:.0f}</b><extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["pred_gb"],
            mode="lines",
            name="Gradient Boosting Forecast",
            line=dict(color=COLORS["accent"], width=2.0, dash="dash"),
            hovertemplate="Date: <b>%{x|%d %b %Y}</b><br>Forecast: <b>%{y:.1f}</b><br>Range: [%{customdata[0]:.0f} – %{customdata[1]:.0f}]<extra></extra>",
            customdata=np.stack((df["pred_p10"], df["pred_p90"]), axis=-1),
        )
    )

    exceedances = df[df["target_next_day_aqi"] > 200]
    if not exceedances.empty:
        fig.add_trace(
            go.Scatter(
                x=exceedances["date"],
                y=exceedances["target_next_day_aqi"],
                mode="markers",
                name="Unhealthy Event (AQI > 200)",
                marker=dict(color="#E5484D", size=6, symbol="circle"),
                hoverinfo="none",
            )
        )

    fig.add_hline(
        y=200,
        line_dash="dot",
        line_color="#E5484D",
        line_width=1.5,
        annotation_text="Unhealthy Threshold (AQI 200)",
        annotation_position="bottom right",
        annotation_font=dict(size=10, color="#E5484D"),
    )

    fig.update_layout(
        title=f"2023 Forward Holdout Validation: Actual vs Forecast at {selected_station}",
        xaxis=dict(
            title="",
            rangeslider=dict(visible=True, thickness=0.06, bgcolor=COLORS["surface"]),
            type="date",
        ),
        yaxis=dict(title="Daily AQI"),
        hovermode="x unified",
        height=430,
        margin=dict(l=45, r=40, t=45, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    )
    return fig

def plot_calibration_and_pr(st_preds: pd.DataFrame) -> go.Figure:
    """
    Renders 2 subplots:
    1. Reliability diagram (calibration curve: predicted prob vs observed freq)
    2. Precision-Recall curve with PR-AUC in title
    """
    df = st_preds.dropna(subset=["target_next_day_unhealthy", "prob_unhealthy"]).copy()
    y_true = df["target_next_day_unhealthy"].values
    y_prob = df["prob_unhealthy"].values

    fig = go.Figure()

    if len(np.unique(y_true)) < 2:
        return fig

    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=8, strategy="uniform")

    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            name="Perfect Calibration Reference",
            line=dict(color="rgba(143, 161, 189, 0.4)", dash="dash", width=1.5),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=prob_pred,
            y=prob_true,
            mode="lines+markers",
            name="Calibrated Model Curve",
            line=dict(color="#00D2FF", width=2.5),
            marker=dict(size=7, color="#00D2FF"),
            hovertemplate="Predicted Prob: <b>%{x:.2f}</b><br>Observed Freq: <b>%{y:.2f}</b><extra></extra>",
        )
    )

    fig.update_layout(
        title="Reliability Diagram: Unhealthy Event Probability (AQI > 200)",
        xaxis=dict(title="Model Predicted Probability", range=[0, 1]),
        yaxis=dict(title="Observed Event Frequency", range=[0, 1]),
        height=320,
        margin=dict(l=45, r=20, t=40, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    )
    return fig

def plot_predicted_vs_actual(st_preds: pd.DataFrame) -> go.Figure:
    """
    Renders parity scatter plot (predicted vs actual) with y=x line
    and interval coverage callout.
    """
    df = st_preds.dropna(subset=["target_next_day_aqi", "pred_gb"]).copy()
    sample = df.sample(min(2000, len(df)), random_state=42)

    in_int = (sample["target_next_day_aqi"] >= sample["pred_p10"]) & (sample["target_next_day_aqi"] <= sample["pred_p90"])
    cov_pct = in_int.mean() * 100

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=sample["target_next_day_aqi"],
            y=sample["pred_gb"],
            mode="markers",
            marker=dict(color=COLORS["accent"], size=5, opacity=0.5),
            name="Observations",
            hovertemplate="Actual: <b>%{x:.0f}</b><br>Predicted: <b>%{y:.0f}</b><extra></extra>",
        )
    )

    max_val = max(sample["target_next_day_aqi"].max(), sample["pred_gb"].max())
    fig.add_trace(
        go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode="lines",
            line=dict(color="#E5484D", width=1.5, dash="dot"),
            name="Parity (y = x)",
        )
    )

    fig.update_layout(
        title=f"Predicted vs Actual AQI (80% Interval Coverage: {cov_pct:.1f}%)",
        xaxis=dict(title="Ground Truth Actual AQI"),
        yaxis=dict(title="Model Predicted AQI"),
        height=320,
        margin=dict(l=45, r=20, t=40, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    )
    return fig
