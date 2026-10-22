"""
CityPulse: Mumbai — Decision Support Visualizations

Charts for what-if simulator, route planning, and rank stability.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from theme import COLORS, get_aqi_category_color


def plot_rank_movement(
    old_priority: pd.DataFrame,
    new_priority: pd.DataFrame,
    top_n: int = 15
) -> go.Figure:
    """
    Visualizes rank changes between two priority rankings.
    Shows top-N stations with movement arrows.
    """
    from src.decision.whatif import compute_rank_delta
    
    delta_df = compute_rank_delta(old_priority, new_priority).head(top_n)
    
    fig = go.Figure()
    
    # Old rank (baseline)
    fig.add_trace(
        go.Scatter(
            x=delta_df["old_rank"],
            y=delta_df["station"],
            mode="markers+text",
            name="Baseline Rank",
            marker=dict(size=10, color=COLORS["text_muted"], symbol="circle"),
            text=delta_df["old_rank"],
            textposition="middle left",
            textfont=dict(size=9, color=COLORS["text_muted"]),
            hovertemplate="<b>%{y}</b><br>Old Rank: #%{x}<extra></extra>",
        )
    )
    
    # New rank (adjusted)
    colors = []
    for delta in delta_df["delta"]:
        if delta > 0:
            colors.append("#2ECC71")  # Moved up (improved)
        elif delta < 0:
            colors.append("#E5484D")  # Moved down (worsened)
        else:
            colors.append(COLORS["text_muted"])  # No change
    
    fig.add_trace(
        go.Scatter(
            x=delta_df["new_rank"],
            y=delta_df["station"],
            mode="markers+text",
            name="Adjusted Rank",
            marker=dict(size=12, color=colors, symbol="diamond"),
            text=delta_df["new_rank"],
            textposition="middle right",
            textfont=dict(size=10, color="#ffffff"),
            hovertemplate="<b>%{y}</b><br>New Rank: #%{x}<br>Change: %{customdata}<extra></extra>",
            customdata=delta_df["movement"],
        )
    )
    
    # Draw arrows for movement
    for _, row in delta_df.iterrows():
        if row["delta"] != 0:
            arrow_color = "#2ECC71" if row["delta"] > 0 else "#E5484D"
            fig.add_annotation(
                x=row["new_rank"],
                y=row["station"],
                ax=row["old_rank"],
                ay=row["station"],
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=arrow_color,
                opacity=0.6,
            )
    
    fig.update_layout(
        title=dict(
            text="How Rankings Change With New Weights",
            font=dict(size=14, color=COLORS["text"]),
        ),
        xaxis=dict(
            title="Rank Position",
            autorange="reversed",
            showgrid=True,
            gridcolor=COLORS["border"],
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            showgrid=False,
        ),
        height=400 + (len(delta_df) * 5),
        margin=dict(l=10, r=10, t=40, b=40),
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"], size=10),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hovermode="closest",
    )
    
    return fig


def plot_rank_stability_ranges(stability_df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """
    Shows rank stability as range plots for top stations.
    Stations with narrow ranges are "robust" to weight changes.
    """
    top_stable = stability_df.head(top_n).copy()
    
    fig = go.Figure()
    
    # Add range bars
    for _, row in top_stable.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[row["rank_min"], row["rank_max"]],
                y=[row["station"], row["station"]],
                mode="lines+markers",
                line=dict(color=COLORS["accent"], width=4),
                marker=dict(size=8, color=COLORS["accent"]),
                name=row["station"],
                showlegend=False,
                hovertemplate=(
                    f"<b>{row['station']}</b><br>"
                    f"Rank Range: #{row['rank_min']} to #{row['rank_max']}<br>"
                    f"Prob in Top-{top_n}: {row['prob_top_n']*100:.1f}%<br>"
                    f"Mean Rank: {row['rank_mean']:.1f}<extra></extra>"
                ),
            )
        )
    
    # Add mean rank as diamond
    fig.add_trace(
        go.Scatter(
            x=top_stable["rank_mean"],
            y=top_stable["station"],
            mode="markers",
            marker=dict(size=10, color="#F5C542", symbol="diamond"),
            name="Mean Rank",
            hoverinfo="skip",
        )
    )
    
    fig.update_layout(
        title=dict(
            text=f"Rank Stability Across Weight Perturbations (Top {top_n})",
            font=dict(size=14, color=COLORS["text"]),
        ),
        xaxis=dict(
            title="Rank Position (Lower is Higher Priority)",
            autorange="reversed",
            showgrid=True,
            gridcolor=COLORS["border"],
        ),
        yaxis=dict(
            title="",
            showgrid=False,
        ),
        height=300 + (len(top_stable) * 25),
        margin=dict(l=10, r=10, t=40, b=40),
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"], size=10),
        hovermode="closest",
    )
    
    return fig


def plot_inspection_route_map(route_df: pd.DataFrame, selected_station: str = None) -> go.Figure:
    """
    Draws the inspection route on a map with numbered stops and path lines.
    """
    use_modern_map = hasattr(go, "Scattermap")
    scatter_cls = go.Scattermap if use_modern_map else go.Scattermapbox
    
    fig = go.Figure()
    
    # Draw route line
    fig.add_trace(
        scatter_cls(
            lat=route_df["latitude"],
            lon=route_df["longitude"],
            mode="lines",
            line=dict(color="#00D2FF", width=3),
            name="Route",
            hoverinfo="skip",
        )
    )
    
    # Draw station markers with numbers
    colors = []
    for i in range(len(route_df)):
        _, cat_color = get_aqi_category_color(route_df.iloc[i]["latest_aqi"])
        colors.append(cat_color)
    
    fig.add_trace(
        scatter_cls(
            lat=route_df["latitude"],
            lon=route_df["longitude"],
            mode="markers+text",
            marker=dict(
                size=20,
                color=colors,
                line=dict(color="#ffffff", width=2),
            ),
            text=route_df["stop_number"],
            textfont=dict(size=11, color="#ffffff", family="Arial Black"),
            textposition="middle center",
            customdata=np.stack(
                (
                    route_df["station"],
                    route_df["zone"],
                    route_df["latest_aqi"],
                    route_df["distance_from_prev_km"],
                    route_df["cumulative_distance_km"],
                ),
                axis=-1,
            ),
            hovertemplate=(
                "<b>Stop #%{text}: %{customdata[0]}</b><br>"
                "Zone: %{customdata[1]}<br>"
                "AQI: %{customdata[2]:.0f}<br>"
                "Distance from previous: %{customdata[3]:.1f} km<br>"
                "Cumulative: %{customdata[4]:.1f} km"
                "<extra></extra>"
            ),
            name="Inspection Stops",
        )
    )
    
    center_lat = route_df["latitude"].mean()
    center_lon = route_df["longitude"].mean()
    
    map_config = dict(
        style="carto-darkmatter",
        center=dict(lat=center_lat, lon=center_lon),
        zoom=10.5,
    )
    
    if use_modern_map:
        fig.update_layout(map=map_config, margin=dict(l=0, r=0, t=10, b=0), height=450)
    else:
        fig.update_layout(mapbox=map_config, margin=dict(l=0, r=0, t=10, b=0), height=450)
    
    return fig


def plot_probability_heatmap(stability_df: pd.DataFrame, top_n: int = 5) -> go.Figure:
    """
    Heatmap showing probability of each station being in top-N.
    """
    top_stations = stability_df.head(15).copy()
    
    fig = go.Figure(
        data=go.Bar(
            x=top_stations["prob_top_n"] * 100,
            y=top_stations["station"],
            orientation="h",
            marker=dict(
                color=top_stations["prob_top_n"],
                colorscale="RdYlGn",
                showscale=True,
                colorbar=dict(
                    title="Probability",
                    ticksuffix="%",
                    tickvals=[0, 0.25, 0.5, 0.75, 1.0],
                    ticktext=["0%", "25%", "50%", "75%", "100%"],
                ),
            ),
            text=[f"{p*100:.0f}%" for p in top_stations["prob_top_n"]],
            textposition="inside",
            textfont=dict(size=11, color="#ffffff"),
            hovertemplate="<b>%{y}</b><br>Probability in Top-%{customdata}: <b>%{x:.1f}%</b><extra></extra>",
            customdata=[top_n] * len(top_stations),
        )
    )
    
    fig.update_layout(
        title=dict(
            text=f"Robustness: Probability of Being in Top {top_n}",
            font=dict(size=14, color=COLORS["text"]),
        ),
        xaxis=dict(
            title="Probability (%)",
            range=[0, 100],
            showgrid=True,
            gridcolor=COLORS["border"],
        ),
        yaxis=dict(
            title="",
            showgrid=False,
        ),
        height=350 + (len(top_stations) * 8),
        margin=dict(l=10, r=10, t=40, b=40),
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"], size=10),
    )
    
    return fig
