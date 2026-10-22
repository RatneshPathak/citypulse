"""
CityPulse: Mumbai — Reusable UI Components
HTML/Streamlit card components, KPI tiles, badges, and dossiers.
Presentation layer with native Material Symbols icons and zero emojis.
"""
import streamlit as st
from theme import COLORS, AQI_PALETTE, get_aqi_category_color
from icons import ICONS
from config import EVENT_NAME, TEAM_MEMBERS, DISCLAIMER_TEXT


def render_compact_banner():
    """Renders a concise, professional regulatory disclaimer banner."""
    st.warning(
        "**Decision-Support Prototype:** For municipal environmental planning (BMC/MPCB role). Not an official statutory emergency warning system. Grounded in verified CPCB and Open-Meteo public data.",
        icon=":material/warning:",
    )


def render_header(station_name: str, date_str: str, total_stations: int = 37):
    """Renders the compact hero header with data freshness and station chips."""
    st.title(f"{ICONS['app_logo']} CityPulse: Mumbai")
    st.caption(
        f"Municipal Air Quality Prioritisation & Early-Warning Decision Support • Greater Mumbai & Navi Mumbai &nbsp;|&nbsp; "
        f"{ICONS['network']} **Network:** {total_stations} CAAQMS Stations &nbsp;|&nbsp; "
        f"{ICONS['calendar']} **Data as of:** {date_str} &nbsp;|&nbsp; "
        f"{ICONS['location']} **Station:** {station_name}"
    )


def render_takeaway(text: str, highlight: str = "Key Decision Takeaway:"):
    """Renders a prominent, plain-language 'So what?' takeaway box at the top of each tab."""
    st.info(f"**{highlight}** {text}", icon=":material/lightbulb:")


def render_kpi_card(
    label: str,
    value: str,
    subtext: str = "",
    color_accent: str | None = None,
    badge: str | None = None,
):
    """Renders a sleek KPI metric card with no whitespace indentation to prevent markdown code block bugs."""
    border_style = f"border-left: 4px solid {color_accent};" if color_accent else ""
    badge_html = f"<span style='background: rgba(255,255,255,0.1); border-radius: 4px; padding: 2px 6px; font-size: 0.68rem;'>{badge}</span>" if badge else ""
    val_color = color_accent if color_accent else "#ffffff"

    html = (
        f'<div class="cp-kpi-card" style="{border_style}">'
        f'<div class="cp-kpi-label"><span>{label}</span>{badge_html}</div>'
        f'<div class="cp-kpi-val" style="color: {val_color};">{value}</div>'
        f'<div class="cp-kpi-sub">{subtext}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_action_strip(priority_df, top_n: int = 5):
    """Renders a compact horizontal action cards strip for top priority zones."""
    st.markdown(f"##### {ICONS['action_queue']} Immediate Municipal Action Queue (Top Priority Zones)")
    top_rows = priority_df.head(top_n)

    surf = COLORS["surface"]
    border = COLORS["border"]
    muted = COLORS["text_muted"]
    accent = COLORS["accent"]

    cols = st.columns(top_n)
    for i, (_, row) in enumerate(top_rows.iterrows()):
        _, cat_col = get_aqi_category_color(row["latest_aqi"])
        rank = row["rank"]
        station = row["station"][:14]
        latest_aqi = row["latest_aqi"]
        prio_score = row["priority_score"]
        zone = row["zone"]
        action = row["recommended_action"][:85]

        with cols[i]:
            card_html = (
                f'<div style="background: {surf}; border: 1px solid {border}; border-top: 3px solid {cat_col}; border-radius: 10px; padding: 12px 14px; height: 100%;">'
                f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">'
                f'<span style="font-weight: 700; font-size: 0.85rem; color: #ffffff;">#{rank} {station}..</span>'
                f'<span style="background: {cat_col}; color: #000000; font-weight: 700; font-size: 0.72rem; padding: 1px 6px; border-radius: 12px;">{latest_aqi:.0f}</span>'
                f'</div>'
                f'<div style="font-size: 0.76rem; color: {muted}; margin-bottom: 6px;">'
                f'Score: <strong style="color: #ffffff;">{prio_score:.1f}</strong> • {zone}'
                f'</div>'
                f'<div style="font-size: 0.72rem; color: {accent}; font-weight: 500; line-height: 1.3;">'
                f'→ {action}...'
                f'</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)


def render_action_dossier(st_data: dict, allocated: bool = True):
    """Renders the comprehensive action dossier for the selected zone."""
    cat_name, cat_col = get_aqi_category_color(st_data["latest_aqi"])
    status_pill = (
        f"<span style='background:#fee2e2; color:#b91c1c; padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.80rem;'>ALLOCATED FOR INSPECTION (Rank #{st_data['rank']})</span>"
        if allocated
        else f"<span style='background:#f1f5f9; color:#475569; padding:3px 10px; border-radius:20px; font-weight:700; font-size:0.80rem;'>ROUTINE MONITORING (Rank #{st_data['rank']})</span>"
    )

    station = st_data["station"]
    action = st_data["recommended_action"]
    evidence = st_data["evidence_basis"]
    caveats = st_data["action_caveats"]
    surf_raised = COLORS["surface_raised"]
    border = COLORS["border"]

    dossier_html = (
        f'<div class="cp-action-dossier" style="border-left-color: {cat_col};">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">'
        f'<h3 class="cp-action-title">Action Protocol: {station}</h3>'
        f'<div>{status_pill}</div>'
        f'</div>'
        f'<div class="cp-action-text">'
        f'<span style="font-size: 1.05rem; font-weight: 600; color: #ffffff;">Recommended Municipal Intervention:</span><br>'
        f'<div style="margin-top: 6px; font-size: 0.96rem; color: #f1f5f9; background: {surf_raised}; border: 1px solid {border}; border-radius: 8px; padding: 12px 16px;">'
        f'{action}'
        f'</div>'
        f'</div>'
        f'<div class="cp-evidence-grid">'
        f'<div><strong style="color: #ffffff;">Verifiable Evidence Basis:</strong><br>{evidence}</div>'
        f'<div><strong style="color: #ffffff;">Operational Caveats:</strong><br>{caveats}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(dossier_html, unsafe_allow_html=True)


def render_source_card(
    name: str,
    provider: str,
    licence: str,
    access_date: str,
    status: str,
    fields: str,
    details: str,
):
    """Renders a data provenance card for Tab 5."""
    status_col = {"USED": "#2ECC71", "SUPPLEMENTARY": "#F5C542"}.get(status, "#E5484D")
    surf = COLORS["surface"]
    border = COLORS["border"]
    muted = COLORS["text_muted"]
    text = COLORS["text"]

    card_html = (
        f'<div style="background: {surf}; border: 1px solid {border}; border-radius: 12px; padding: 16px 20px; margin-bottom: 12px;">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">'
        f'<h4 style="margin: 0; color: #ffffff; font-size: 1rem; font-weight: 600;">{name}</h4>'
        f'<div style="display: flex; gap: 6px;">'
        f'<span style="background: rgba(255,255,255,0.08); border-radius: 4px; padding: 2px 8px; font-size: 0.72rem; color: {muted};">{licence}</span>'
        f'<span style="background: {status_col}22; border: 1px solid {status_col}; color: {status_col}; border-radius: 4px; padding: 2px 8px; font-size: 0.72rem; font-weight: 700;">{status}</span>'
        f'</div>'
        f'</div>'
        f'<div style="font-size: 0.82rem; color: {muted}; margin-bottom: 8px;">'
        f'<strong>Provider:</strong> {provider} • <strong>Accessed:</strong> {access_date}'
        f'</div>'
        f'<div style="font-size: 0.82rem; color: {text}; line-height: 1.4;">'
        f'<strong>Fields / Usage:</strong> {fields}<br>'
        f'<span style="color: {muted};">{details}</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_footer():
    """Renders the persistent HackAMatch credit & data provenance footer."""
    footer_html = (
        f'<div class="cp-footer">'
        f'<div class="cp-footer-primary">Built for <strong>{EVENT_NAME}</strong> by <strong>{TEAM_MEMBERS}</strong></div>'
        f'<div class="cp-footer-secondary">{DISCLAIMER_TEXT}</div>'
        f'</div>'
    )
    st.markdown(footer_html, unsafe_allow_html=True)
