"""
CityPulse: Mumbai — Design System & Theme Engine
Theme configuration, color palettes, typography, and Plotly templates.
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

COLORS = {
    "bg": "#0B1220",
    "background": "#0B1220",
    "surface": "#162235",
    "surface_raised": "#1C2B42",
    "surface_hover": "#223552",
    "border": "#24364F",
    "border_focus": "#2DD4BF",
    "text": "#F1F5F9",
    "text_muted": "#94A3B8",
    "accent": "#2DD4BF",          
    "accent_subtle": "rgba(45, 212, 191, 0.12)",
    "accent_secondary": "#38BDF8", 
    "warning": "#F59E0B",           
    "info": "#38BDF8",              
    "critical": "#EF4444",       
    "success": "#10B981",           
}

AQI_PALETTE = {
    "Good": "#10B981",
    "Satisfactory": "#84CC16",
    "Moderate": "#F59E0B",
    "Poor": "#F97316",
    "Very Poor": "#EF4444",
    "Severe": "#A855F7",
    "Missing": "#64748B",
}

AQI_BREAKPOINTS = [
    (0, 50, "Good", "#10B981"),
    (50, 100, "Satisfactory", "#84CC16"),
    (100, 200, "Moderate", "#F59E0B"),
    (200, 300, "Poor", "#F97316"),
    (300, 400, "Very Poor", "#EF4444"),
    (400, 700, "Severe", "#A855F7"),
]

PRIORITY_PALETTE = {
    "Highest": "#EF4444",      
    "Elevated": "#F59E0B",     
    "Moderate": "#38BDF8",   
    "Routine": "#64748B",     
}

def get_priority_tier(rank: int, capacity_n: int = 5) -> tuple[str, str]:
    """Returns (tier_label, hex_color) for an inspection priority rank."""
    if rank <= capacity_n:
        return ("Highest Priority", PRIORITY_PALETTE["Highest"])
    elif rank <= capacity_n * 2:
        return ("Elevated Priority", PRIORITY_PALETTE["Elevated"])
    elif rank <= capacity_n * 3:
        return ("Moderate Priority", PRIORITY_PALETTE["Moderate"])
    return ("Routine Monitoring", PRIORITY_PALETTE["Routine"])

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
    """Configures and registers the CityPulse command center dark theme in Plotly."""
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
            font=dict(size=15, color=COLORS["text"], weight=600),
            x=0.0,
            xanchor="left",
            pad=dict(b=10),
        ),
        xaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.08)",
            linecolor=COLORS["border"],
            zerolinecolor="rgba(148, 163, 184, 0.12)",
            tickfont=dict(color=COLORS["text_muted"], size=11),
            title=dict(font=dict(color=COLORS["text_muted"], size=12)),
        ),
        yaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.08)",
            linecolor=COLORS["border"],
            zerolinecolor="rgba(148, 163, 184, 0.12)",
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
            bgcolor="rgba(22, 34, 53, 0.8)",
            bordercolor=COLORS["border"],
            borderwidth=1,
        ),
        colorway=[
            COLORS["accent"],
            COLORS["accent_secondary"],
            COLORS["warning"],
            COLORS["success"],
            COLORS["critical"],
            "#84CC16",
            "#A855F7",
        ],
        margin=dict(l=45, r=20, t=45, b=40),
    )
    pio.templates["citypulse_dark"] = template
    pio.templates.default = "citypulse_dark"

register_plotly_theme()

def inject_custom_css():
    """Injects command center custom styling into Streamlit."""
    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

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
            padding-top: 1.25rem !important;
            padding-bottom: 3rem !important;
            max-width: 1400px !important;
        }}

        [data-testid="stSidebar"] {{
            background-color: #0E1726;
            border-right: 1px solid {COLORS["border"]};
        }}
        [data-testid="stSidebar"] hr {{
            margin: 0.9rem 0;
            border-color: {COLORS["border"]};
        }}

        .cp-cmd-header {{
            background: linear-gradient(135deg, {COLORS["surface"]} 0%, #111D30 100%);
            border: 1px solid {COLORS["border"]};
            border-radius: 12px;
            padding: 18px 24px;
            margin-bottom: 0.9rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
        }}
        .cp-cmd-branding {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .cp-cmd-icon {{
            width: 44px;
            height: 44px;
            background: {COLORS["accent_subtle"]};
            border: 1px solid {COLORS["accent"]};
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            overflow: hidden;
        }}
        .cp-cmd-titles {{
            display: flex;
            flex-direction: column;
        }}
        .cp-cmd-kicker {{
            color: {COLORS["accent"]};
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }}
        .cp-cmd-name {{
            font-size: 1.6rem;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.02em;
            margin: 0;
            line-height: 1.2;
        }}
        .cp-cmd-tagline {{
            font-size: 0.85rem;
            color: {COLORS["text_muted"]};
            margin: 2px 0 0 0;
        }}
        .cp-cmd-badges {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}

        /* Transparent Data-Status Bar */
        .cp-status-bar {{
            background: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 10px;
            padding: 10px 16px;
            margin-bottom: 1.25rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        }}
        .cp-status-items {{
            display: flex;
            align-items: center;
            gap: 18px;
            flex-wrap: wrap;
        }}
        .cp-status-item {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        .cp-status-label {{
            font-size: 0.68rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {COLORS["text_muted"]};
        }}
        .cp-status-value {{
            font-size: 0.82rem;
            font-weight: 600;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 5px;
        }}

        .cp-pill {{
            background: {COLORS["surface_raised"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 999px;
            padding: 3px 10px;
            font-size: 0.74rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}
        .cp-pill-amber {{
            background: rgba(245, 158, 11, 0.12);
            border-color: rgba(245, 158, 11, 0.4);
            color: #FBBF24;
        }}
        .cp-pill-teal {{
            background: {COLORS["accent_subtle"]};
            border-color: {COLORS["accent"]};
            color: {COLORS["accent"]};
        }}
        .cp-pill-red {{
            background: rgba(239, 68, 68, 0.12);
            border-color: rgba(239, 68, 68, 0.4);
            color: #F87171;
        }}
        .cp-pill-green {{
            background: rgba(16, 185, 129, 0.12);
            border-color: rgba(16, 185, 129, 0.4);
            color: #34D399;
        }}

        /* KPI Cards */
        .cp-kpi-card {{
            background: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-top: 3px solid {COLORS["accent"]};
            border-radius: 12px;
            padding: 16px 18px;
            transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
            position: relative;
            overflow: hidden;
            height: 100%;
        }}
        .cp-kpi-card:hover {{
            transform: translateY(-2px);
            border-color: {COLORS["border_focus"]};
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
        }}
        .cp-kpi-label {{
            font-size: 0.73rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: {COLORS["text_muted"]};
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .cp-kpi-val {{
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #ffffff;
            line-height: 1.1;
        }}
        .cp-kpi-sub {{
            font-size: 0.78rem;
            color: {COLORS["text_muted"]};
            margin-top: 6px;
            line-height: 1.35;
        }}

        /* Top Priority Action Queue */
        .cp-queue-card {{
            background: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-top: 3px solid {COLORS["accent"]};
            border-radius: 10px;
            padding: 14px 16px;
            margin-bottom: 10px;
            box-shadow: 0 3px 12px rgba(0, 0, 0, 0.2);
            transition: all 0.15s ease;
        }}
        .cp-queue-card:hover {{
            border-color: {COLORS["border_focus"]};
            transform: translateY(-1px);
        }}
        .cp-queue-top {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .cp-queue-rank {{
            color: {COLORS["text_muted"]};
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .cp-queue-station {{
            color: #ffffff;
            font-size: 1.02rem;
            font-weight: 700;
            line-height: 1.3;
        }}
        .cp-queue-meta {{
            color: {COLORS["text_muted"]};
            font-size: 0.78rem;
            margin: 4px 0 10px;
        }}
        .cp-queue-action {{
            color: {COLORS["text"]};
            font-size: 0.84rem;
            line-height: 1.45;
        }}

        /* Action Dossier */
        .cp-action-dossier {{
            background: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-left: 5px solid {COLORS["accent"]};
            border-radius: 12px;
            padding: 18px 22px;
            margin-top: 1rem;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
        }}
        .cp-action-title {{
            font-size: 1.05rem;
            font-weight: 700;
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

        /* Section navigation styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
            background-color: {COLORS["surface"]};
            border-radius: 10px;
            padding: 6px;
            border: 1px solid {COLORS["border"]};
            margin-bottom: 1.25rem;
            overflow-x: auto;
            scrollbar-width: thin;
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
            color: #0B1220 !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 8px rgba(45, 212, 191, 0.3) !important;
        }}
        .stTabs [data-baseweb="tab"]:focus-visible,
        button:focus-visible {{
            outline: 2px solid {COLORS["accent"]} !important;
            outline-offset: 2px !important;
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid {COLORS["border"]};
            border-radius: 10px;
            overflow: hidden;
            background-color: {COLORS["surface"]};
        }}

        /* Sidebar radio navigation */
        [data-testid="stSidebar"] [data-testid="stRadio"] > div {{
            background: transparent;
            gap: 4px;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label {{
            background-color: rgba(22, 34, 53, 0.6);
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            padding: 8px 12px;
            margin-bottom: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
            background-color: {COLORS["surface_hover"]};
            border-color: {COLORS["accent"]};
        }}

        .cp-footer {{
            margin-top: 3.5rem;
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            border-top: 1px solid rgba(148, 163, 184, 0.15);
            text-align: center;
        }}
        .cp-footer-primary {{
            font-size: 0.92rem;
            font-weight: 500;
            color: #E2E8F0;
            margin-bottom: 6px;
        }}
        .cp-footer-primary strong {{
            color: #FFFFFF;
            font-weight: 700;
        }}
        .cp-footer-secondary {{
            font-size: 0.75rem;
            color: {COLORS["text_muted"]};
            opacity: 0.9;
            line-height: 1.5;
            max-width: 820px;
            margin: 0 auto;
        }}

        @media (max-width: 640px) {{
            .block-container {{ padding: 0.8rem 0.8rem 2rem !important; }}
            .cp-cmd-header {{ padding: 14px; }}
            .cp-cmd-name {{ font-size: 1.3rem; }}
            .cp-status-bar {{ padding: 10px 12px; }}
            .cp-status-items {{ gap: 10px; }}
            .cp-evidence-grid {{ grid-template-columns: 1fr; }}
            .cp-action-dossier {{ padding: 14px; }}
            .stTabs [data-baseweb="tab"] {{ padding: 6px 10px !important; }}
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
