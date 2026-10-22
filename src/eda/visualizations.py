"""
CityPulse: Mumbai — Core EDA Visualization Library
Reusable, publication-grade Plotly chart functions extracted directly from the
team's source-of-truth notebook (src/CityPulse_AQI_Cleaning_EDA.ipynb).

These functions power both the interactive narrative notebook and the Streamlit app's
Evidence panel.
"""
from typing import List, Optional, Union
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

THEME = {
    "bg": "#0B1220",
    "surface": "#111A2B",
    "surface_raised": "#172238",
    "border": "#24324D",
    "text": "#E6EDF7",
    "text_muted": "#8FA2BC",
    "accent": "#4F8BFF",
    "warning": "#F59E0B",
    "critical": "#EF4444",
    "success": "#10B981",
    "info": "#06B6D4",
    "station_palette": [
        "#4F8BFF",
        "#10B981",
        "#F59E0B",
        "#A855F7",
        "#EC4899",
    ],
}


def _apply_dark_layout(fig: go.Figure, title: str, subtitle: Optional[str] = None, height: int = 400) -> go.Figure:
    """Applies cohesive dark-theme formatting to any Plotly figure."""
    full_title = f"<b>{title}</b>"
    if subtitle:
        full_title += f"<br><span style='font-size: 11px; color: {THEME['text_muted']}; font-weight: normal;'>{subtitle}</span>"

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=THEME["surface"],
        margin=dict(l=40, r=25, t=55 if subtitle else 40, b=40),
        height=height,
        title=dict(
            text=full_title,
            font=dict(family="Inter, sans-serif", size=14, color=THEME["text"]),
            x=0.01,
            y=0.96,
        ),
        font=dict(family="Inter, sans-serif", color=THEME["text"], size=11),
        xaxis=dict(
            showgrid=True,
            gridcolor=THEME["border"],
            zeroline=False,
            tickfont=dict(color=THEME["text_muted"], size=10),
            title_font=dict(color=THEME["text"], size=11),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=THEME["border"],
            zeroline=False,
            tickfont=dict(color=THEME["text_muted"], size=10),
            title_font=dict(color=THEME["text"], size=11),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(color=THEME["text"], size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor=THEME["surface_raised"],
            bordercolor=THEME["border"],
            font=dict(family="Inter, sans-serif", size=11, color=THEME["text"]),
        ),
    )
    return fig


def plot_station_comparison(
    df: pd.DataFrame,
    pollutants: Optional[List[str]] = None,
    height: int = 400
) -> go.Figure:
    """
    Renders grouped bar chart of mean pollutant concentrations across stations.
    Direct implementation of Notebook Cells 9-10.
    """
    if pollutants is None:
        pollutants = ["PM2.5", "PM10"]

    avail_pollutants = [p for p in pollutants if p in df.columns]
    if not avail_pollutants or "Station" not in df.columns:
        fig = go.Figure()
        return _apply_dark_layout(fig, "Station Comparison — No Data", height=height)

    means = df.groupby("Station")[avail_pollutants].mean().reset_index()

    means["Short_Station"] = means["Station"].str.replace(", Mumbai - IITM", "").str.replace(", Mumbai - MPCB", "")

    fig = go.Figure()
    palette = [THEME["accent"], THEME["warning"], THEME["info"], THEME["critical"]]
    for idx, pol in enumerate(avail_pollutants):
        fig.add_trace(
            go.Bar(
                x=means["Short_Station"],
                y=means[pol],
                name=f"{pol} (µg/m³)",
                marker_color=palette[idx % len(palette)],
                text=means[pol].round(1),
                textposition="outside",
                textfont=dict(size=10, color=THEME["text"]),
                hovertemplate="<b>%{x}</b><br>" + pol + ": <b>%{y:.2f} µg/m³</b><extra></extra>",
            )
        )

    fig.update_layout(barmode="group")
    return _apply_dark_layout(
        fig,
        title="Spatial Contrast: Mean Particulate Concentrations Across Stations",
        subtitle="BKC records highest particulate exposure; Borivali East cleanest. Source: CPCB continuous data.",
        height=height,
    )


def plot_monthly_trends(
    df: pd.DataFrame,
    pollutant: str = "PM2.5",
    height: int = 420
) -> go.Figure:
    """
    Renders monthly seasonal trend lines per station demonstrating the U-shaped monsoon washout.
    Direct implementation of Notebook Cells 11-13.
    """
    if df.empty or pollutant not in df.columns or "From Date" not in df.columns:
        return _apply_dark_layout(go.Figure(), f"Monthly {pollutant} Trends — No Data", height=height)

    temp_df = df.dropna(subset=["From Date", pollutant]).copy()
    if not pd.api.types.is_datetime64_any_dtype(temp_df["From Date"]):
        temp_df["From Date"] = pd.to_datetime(temp_df["From Date"], dayfirst=True, errors="coerce")

    temp_df["Month_Year"] = temp_df["From Date"].dt.to_period("M").astype(str)

    monthly_stats = (
        temp_df.groupby(["Month_Year", "Station"])[pollutant]
        .mean()
        .reset_index()
        .sort_values("Month_Year")
    )

    fig = go.Figure()
    stations = monthly_stats["Station"].unique()

    for idx, station in enumerate(stations):
        sub = monthly_stats[monthly_stats["Station"] == station]
        clean_name = station.replace(", Mumbai - IITM", "").replace(", Mumbai - MPCB", "")
        color = THEME["station_palette"][idx % len(THEME["station_palette"])]
        fig.add_trace(
            go.Scatter(
                x=sub["Month_Year"],
                y=sub[pollutant],
                mode="lines+markers",
                name=clean_name,
                line=dict(color=color, width=2.5),
                marker=dict(size=5),
                hovertemplate=f"<b>{clean_name}</b><br>Month: %{{x}}<br>{pollutant}: <b>%{{y:.1f}} µg/m³</b><extra></extra>",
            )
        )

    if pollutant == "PM2.5":
        fig.add_hline(
            y=40,
            line_dash="dot",
            line_color=THEME["warning"],
            line_width=1.5,
            annotation_text="NAAQS Standard (40 µg/m³)",
            annotation_position="top left",
            annotation_font=dict(size=9, color=THEME["warning"]),
        )

    return _apply_dark_layout(
        fig,
        title=f"Seasonal Trajectory: Monthly Mean {pollutant} Concentrations",
        subtitle="Pronounced U-shape: Monsoon washout (Jul–Aug <15 µg/m³) vs. Winter inversion peak (Nov–Dec >70 µg/m³).",
        height=height,
    )


def plot_diurnal_cycle(
    df: pd.DataFrame,
    pollutant: str = "PM2.5",
    height: int = 400
) -> go.Figure:
    """
    Renders 24-hour diurnal profile showing morning and evening traffic/atmospheric peaks.
    Direct implementation of Notebook Cells 19-20.
    """
    if df.empty or pollutant not in df.columns or "From Date" not in df.columns:
        return _apply_dark_layout(go.Figure(), f"Diurnal Cycle ({pollutant}) — No Data", height=height)

    temp_df = df.dropna(subset=["From Date", pollutant]).copy()
    if not pd.api.types.is_datetime64_any_dtype(temp_df["From Date"]):
        temp_df["From Date"] = pd.to_datetime(temp_df["From Date"], dayfirst=True, errors="coerce")

    temp_df["Hour"] = temp_df["From Date"].dt.hour

    fig = go.Figure()

    stations = temp_df["Station"].unique()
    for idx, station in enumerate(stations):
        sub = temp_df[temp_df["Station"] == station]
        hourly = sub.groupby("Hour")[pollutant].mean().reset_index()
        clean_name = station.replace(", Mumbai - IITM", "").replace(", Mumbai - MPCB", "")
        color = THEME["station_palette"][idx % len(THEME["station_palette"])]
        fig.add_trace(
            go.Scatter(
                x=hourly["Hour"],
                y=hourly[pollutant],
                mode="lines",
                name=clean_name,
                line=dict(color=color, width=2),
                hovertemplate=f"<b>{clean_name}</b><br>Hour: %{{x}}:00<br>{pollutant}: <b>%{{y:.1f}} µg/m³</b><extra></extra>",
            )
        )

    city_hourly = temp_df.groupby("Hour")[pollutant].mean().reset_index()
    fig.add_trace(
        go.Scatter(
            x=city_hourly["Hour"],
            y=city_hourly[pollutant],
            mode="lines+markers",
            name="City Mean",
            line=dict(color="#FFFFFF", width=3.5, dash="solid"),
            marker=dict(size=6, color="#FFFFFF"),
            hovertemplate="<b>City Average</b><br>Hour: %{x}:00<br>" + pollutant + ": <b>%{y:.1f} µg/m³</b><extra></extra>",
        )
    )

    fig.update_xaxes(
        tickmode="linear",
        tick0=0,
        dtick=2,
        title_text="Hour of Day (IST)",
    )
    fig.update_yaxes(title_text=f"{pollutant} (µg/m³)")

    return _apply_dark_layout(
        fig,
        title=f"Diurnal Pulse: 24-Hour Cycle of {pollutant} in Mumbai",
        subtitle="Bimodal profile: Morning commute (08:00–10:00) and nocturnal boundary layer stagnation (20:00–23:00).",
        height=height,
    )


def plot_distribution_boxplots(
    df: pd.DataFrame,
    pollutant: str = "PM2.5",
    height: int = 400
) -> go.Figure:
    """
    Renders boxplots per station displaying median, IQR, and extreme episodic tail events.
    Direct implementation of Notebook Cell 16.
    """
    if df.empty or pollutant not in df.columns:
        return _apply_dark_layout(go.Figure(), f"Distribution ({pollutant}) — No Data", height=height)

    temp_df = df.dropna(subset=[pollutant]).copy()
    temp_df["Short_Station"] = temp_df["Station"].str.replace(", Mumbai - IITM", "").str.replace(", Mumbai - MPCB", "")

    fig = go.Figure()
    stations = temp_df["Short_Station"].unique()

    for idx, station in enumerate(stations):
        sub = temp_df[temp_df["Short_Station"] == station]
        color = THEME["station_palette"][idx % len(THEME["station_palette"])]
        fig.add_trace(
            go.Box(
                y=sub[pollutant],
                name=station,
                marker_color=color,
                boxpoints="outliers",
                jitter=0.2,
                pointpos=-1.5,
                line=dict(width=1.5),
            )
        )

    fig.update_yaxes(title_text=f"{pollutant} (µg/m³)")
    return _apply_dark_layout(
        fig,
        title=f"Variability & Tail Risk: {pollutant} Dispersion by Monitoring Station",
        subtitle="Long positive tails show frequent acute episodic spikes exceeding 200 µg/m³.",
        height=height,
    )


def plot_outlier_summary(
    df_or_outliers: pd.DataFrame,
    pollutant: str = "PM2.5",
    height: int = 380
) -> go.Figure:
    """
    Visualizes outlier prevalence across monitoring stations based on Tukey IQR bounds.
    Direct implementation of Notebook Cells 17-18.
    """
    if df_or_outliers.empty:
        return _apply_dark_layout(go.Figure(), "Outlier Summary — No Data", height=height)

    if "lower_bound" not in df_or_outliers.columns and pollutant in df_or_outliers.columns:
        from src.clean.aqi_cleaning import detect_outliers_iqr
        outlier_data = detect_outliers_iqr(df_or_outliers, pollutant=pollutant)
    else:
        outlier_data = df_or_outliers

    if outlier_data.empty:
        return _apply_dark_layout(go.Figure(), f"No Outliers Detected for {pollutant}", height=height)

    counts = outlier_data["Station"].value_counts().reset_index()
    counts.columns = ["Station", "Outlier_Count"]
    counts["Short_Station"] = counts["Station"].str.replace(", Mumbai - IITM", "").str.replace(", Mumbai - MPCB", "")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=counts["Short_Station"],
            y=counts["Outlier_Count"],
            marker_color=THEME["warning"],
            text=counts["Outlier_Count"],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Flagged Outliers: <b>%{y}</b><extra></extra>",
        )
    )

    fig.update_yaxes(title_text="Count of Flagged Readings (1.5x IQR)")
    return _apply_dark_layout(
        fig,
        title=f"Statistical Outliers: Readings Beyond 1.5× IQR ({pollutant})",
        subtitle="Outliers preserved: Physical emissions events (industrial flaring, Diwali, inversions) rather than sensor glitches.",
        height=height,
    )
