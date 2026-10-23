"""
CityPulse: Mumbai — Design System & Theme Engine
Theme configuration, color palettes, typography, and Plotly templates.
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

COLORS = {
    "bg": "#0B1220",
    "surface": "#111A2B",
    "surface_raised": "#172238",
    "surface_hover": "#1E2C48",
    "border": "#24324D",
    "border_focus": "#3B527A",
    "text": "#E6EDF7",
    "text_muted": "#8FA1BD",
    "accent": "#4F8CFF",
    "accent_subtle": "rgba(79, 140, 255, 0.15)",
    "accent_secondary": "#00D2FF",
    "warning": "#F5C542",
    "info": "#00D2FF",
    "critical": "#E5484D",
    "success": "#2ECC71",
}

AQI_PALETTE = {
    "Good": "#2ECC71",
    "Satisfactory": "#A3D86B",
    "Moderate": "#F5C542",
    "Poor": "#F08A3C",
    "Very Poor": "#E5484D",
    "Severe": "#8E2BA8",
    "Missing": "#64748B"
}

AQI_BREAKPOINTS = [
    (0, 50, "Good", "#2ECC71"),
    (50, 100, "Satisfactory", "#A3D86B"),
    (100, 200, "Moderate", "#F5C542"),
    (200, 300, "Poor", "#F08A3C"),
    (300, 400, "Very Poor", "#E5484D"),
    (400, 700, "Severe", "#8E2BA8"),
]

def get_aqi_category_color(aqi_val: float) -> tuple[str, str]:
    """Returns (category_name, hex_color) for any numeric AQI value."""
    if aqi_val is None or (isinstance(aqi_val, float) and (aqi_val != aqi_val)):
        return ("Missing", AQI_PALETTE["Missing"])
    for low, high, cat, col in AQI_BREAKPOINTS:
        if low <= aqi_val <= high:
            return (cat, col)
    if aqi_val > 400:
        return ("Severe", AQI_PALETTE["Severe"])
    return ("Good", AQI_PALETTE["Good"])

def register_plotly_theme():
    """Configures and registers the CityPulse dark theme in Plotly."""
    template = go.layout.Template()
    template.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            color=COLORS["text"],
            size=12,
        ),
        title=dict(
            font=dict(size=16, color=COLORS["text"], weight=600),
            x=0.0,
            xanchor="left",
            pad=dict(b=10),
        ),
        xaxis=dict(
            gridcolor="rgba(143, 161, 189, 0.08)",
            linecolor=COLORS["border"],
            zerolinecolor="rgba(143, 161, 189, 0.12)",
            tickfont=dict(color=COLORS["text_muted"], size=11),
            title=dict(font=dict(color=COLORS["text_muted"], size=12)),
        ),
        yaxis=dict(
            gridcolor="rgba(143, 161, 189, 0.08)",
            linecolor=COLORS["border"],
            zerolinecolor="rgba(143, 161, 189, 0.12)",
            tickfont=dict(color=COLORS["text_muted"], size=11),
            title=dict(font=dict(color=COLORS["text_muted"], size=12)),
        ),
        hoverlabel=dict(
            bgcolor=COLORS["surface_raised"],
            bordercolor=COLORS["accent"],
            font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
        ),
        legend=dict(
            font=dict(color=COLORS["text"], size=11),
            bgcolor="rgba(17, 26, 43, 0.6)",
            bordercolor=COLORS["border"],
            borderwidth=1,
        ),
        colorway=[
            COLORS["accent"],
            "#00D2FF",
            "#F5C542",
            "#2ECC71",
            "#E5484D",
            "#A3D86B",
            "#9D7BFF",
        ],
        margin=dict(l=45, r=20, t=45, b=40),
    )
    pio.templates["citypulse_dark"] = template
    pio.templates.default = "citypulse_dark"

register_plotly_theme()

def inject_custom_css():
    """Injects high-end, responsive custom styling into Streamlit."""
    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"], [data-testid="stAppViewContainer"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: {COLORS["text"]};
            background-color: {COLORS["bg"]};
        }}

        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        [data-testid="stToolbar"] {{display: none;}}

        .block-container {{
            padding-top: 1.5rem !important;
            padding-bottom: 3rem !important;
            max-width: 1350px !important;
        }}

        [data-testid="stSidebar"] {{
            background-color: {COLORS["surface"]};
            border-right: 1px solid {COLORS["border"]};
        }}
        [data-testid="stSidebar"] hr {{
            margin: 1rem 0;
            border-color: {COLORS["border"]};
        }}

        .cp-hero {{
            background: linear-gradient(135deg, {COLORS["surface"]} 0%, {COLORS["surface_raised"]} 100%);
            border: 1px solid {COLORS["border"]};
            border-radius: 14px;
            padding: 20px 26px;
            margin-bottom: 1.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }}
        .cp-hero-title {{
            font-size: 1.65rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.02em;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .cp-hero-sub {{
            font-size: 0.88rem;
            color: {COLORS["text_muted"]};
            margin: 4px 0 0 0;
        }}
        .cp-chip-group {{
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .cp-chip {{
            background: {COLORS["surface_raised"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 0.78rem;
            font-weight: 500;
            color: {COLORS["text"]};
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .cp-chip-accent {{
            background: {COLORS["accent_subtle"]};
            border: 1px solid {COLORS["accent"]};
            color: #ffffff;
            font-weight: 600;
        }}

        .cp-kpi-card {{
            background: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 14px;
            padding: 16px 18px;
            transition: transform 0.15s ease, border-color 0.15s ease;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
            position: relative;
            overflow: hidden;
        }}
        .cp-kpi-card:hover {{
            transform: translateY(-2px);
            border-color: {COLORS["border_focus"]};
        }}
        .cp-kpi-label {{
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: {COLORS["text_muted"]};
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .cp-kpi-val {{
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: #ffffff;
            line-height: 1.1;
        }}
        .cp-kpi-sub {{
            font-size: 0.78rem;
            color: {COLORS["text_muted"]};
            margin-top: 6px;
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        .cp-takeaway {{
            background: rgba(79, 140, 255, 0.08);
            border-left: 4px solid {COLORS["accent"]};
            border-radius: 8px;
            padding: 12px 18px;
            margin-bottom: 1.25rem;
            font-size: 0.90rem;
            color: {COLORS["text"]};
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }}
        .cp-takeaway-strong {{
            color: #ffffff;
            font-weight: 600;
        }}

        .cp-action-dossier {{
            background: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-left: 5px solid {COLORS["accent"]};
            border-radius: 12px;
            padding: 18px 22px;
            margin-top: 1rem;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        }}
        .cp-action-title {{
            font-size: 1.05rem;
            font-weight: 600;
            color: #ffffff;
            margin: 0 0 10px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .cp-action-text {{
            font-size: 0.95rem;
            color: {COLORS["text"]};
            line-height: 1.5;
            margin-bottom: 12px;
        }}
        .cp-evidence-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            background: {COLORS["surface_raised"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            padding: 12px 14px;
            font-size: 0.82rem;
            color: {COLORS["text_muted"]};
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
            background-color: {COLORS["surface"]};
            border-radius: 10px;
            padding: 6px;
            border: 1px solid {COLORS["border"]};
            margin-bottom: 1.25rem;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px !important;
            padding: 8px 16px !important;
            font-size: 0.88rem !important;
            font-weight: 500 !important;
            color: {COLORS["text_muted"]} !important;
            border: none !important;
            background-color: transparent !important;
            transition: all 0.2s ease !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            color: #ffffff !important;
            background-color: {COLORS["surface_hover"]} !important;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {COLORS["accent"]} !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            box-shadow: 0 2px 8px rgba(79, 140, 255, 0.3) !important;
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid {COLORS["border"]};
            border-radius: 10px;
            overflow: hidden;
        }}

        .cp-banner-compact {{
            background: rgba(245, 197, 66, 0.10);
            border: 1px solid rgba(245, 197, 66, 0.35);
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 0.80rem;
            color: #F5C542;
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 1rem;
        }}

        .cp-footer {{
            margin-top: 3.5rem;
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            border-top: 1px solid rgba(143, 161, 189, 0.2);
            text-align: center;
        }}
        .cp-footer-primary {{
            font-size: 0.95rem;
            font-weight: 500;
            color: #E6EDF7;
            margin-bottom: 6px;
            letter-spacing: -0.01em;
        }}
        .cp-footer-primary strong, .cp-footer-primary b {{
            color: #FFFFFF;
            font-weight: 700;
        }}
        .cp-footer-secondary {{
            font-size: 0.75rem;
            color: #8FA1BD;
            opacity: 0.85;
            line-height: 1.5;
            max-width: 820px;
            margin: 0 auto;
        }}

        [data-testid="stIconMaterial"], .stIcon {{
            vertical-align: -0.18em !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}

        .stTabs [data-baseweb="tab"] [data-testid="stIconMaterial"] {{
            margin-right: 6px !important;
            font-size: 1.05rem !important;
            vertical-align: -0.15em !important;
        }}

        h1 [data-testid="stIconMaterial"],
        h2 [data-testid="stIconMaterial"],
        h3 [data-testid="stIconMaterial"],
        h4 [data-testid="stIconMaterial"],
        h5 [data-testid="stIconMaterial"],
        h6 [data-testid="stIconMaterial"] {{
            vertical-align: -0.15em !important;
            margin-right: 4px !important;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
