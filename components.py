"""
CityPulse: Mumbai — Reusable UI Components
HTML/Streamlit card components, KPI tiles, badges, and dossiers.
Presentation layer with native Material Symbols icons and zero emojis.
"""
from html import escape

import streamlit as st
from theme import COLORS, AQI_PALETTE, get_aqi_category_color
from icons import ICONS
from config import EVENT_NAME, TEAM_MEMBERS, DISCLAIMER_TEXT

def render_compact_banner():
    """Renders a concise, professional regulatory disclaimer banner."""
    st.markdown(
        '<div class="cp-banner-compact" role="note">'
        '<strong>Decision-support prototype</strong><span>For municipal planning and inspection triage. '
        'This is not an official air-quality warning system.</span></div>',
        unsafe_allow_html=True,
    )

def render_header(station_name: str, date_str: str, total_stations: int = 37):
    """Renders the compact hero header with data freshness and station chips."""
    station = escape(station_name)
    date = escape(date_str)
    st.markdown(
        '<div class="cp-hero">'
        '<div class="cp-hero-copy">'
        '<div class="cp-hero-kicker">MUMBAI AIR QUALITY · DECISION CONSOLE</div>'
        '<h1 class="cp-hero-title">CityPulse: Mumbai</h1>'
        '<p class="cp-hero-sub">Explore the evidence, compare risks, and plan inspections.</p>'
        '</div>'
        '<div class="cp-chip-group" aria-label="Current replay context">'
        f'<span class="cp-chip cp-chip-accent">{station}</span>'
        f'<span class="cp-chip">Replay date · {date}</span>'
        f'<span class="cp-chip">{total_stations} monitoring stations</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def render_navigation_guide():
    st.markdown(
        '<div class="cp-journey" aria-label="Dashboard sections">'
        '<div><strong>Decide</strong><span>1–4 · Rank, test weights, route, export</span></div>'
        '<div><strong>Understand</strong><span>5–6, 9 · Patterns, weather, case study</span></div>'
        '<div><strong>Trust</strong><span>7–8, 12 · Forecast checks, validation, sources</span></div>'
        '<div><strong>Share</strong><span>10–11 · Citizen view, guided demo</span></div>'
        '</div>',
        unsafe_allow_html=True,
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
    """Renders readable action cards for top priority zones."""
    st.markdown(f"##### {ICONS['action_queue']} Immediate Municipal Action Queue (Top Priority Zones)")
    top_rows = priority_df.head(top_n)
    if top_rows.empty:
        st.info("No priority zones are available for this replay date.")
        return

    cols = st.columns(min(2, len(top_rows)), gap="medium")
    for i, (_, row) in enumerate(top_rows.iterrows()):
        _, cat_col = get_aqi_category_color(row["latest_aqi"])
        rank = row["rank"]
        station = escape(str(row["station"]))
        latest_aqi = row["latest_aqi"]
        prio_score = row["priority_score"]
        zone = escape(str(row["zone"]))
        action = escape(str(row["recommended_action"]))

        with cols[i % len(cols)]:
            card_html = (
                f'<div class="cp-queue-card" style="border-top-color: {cat_col};">'
                f'<div class="cp-queue-top">'
                f'<span class="cp-queue-rank">Priority #{rank}</span>'
                f'<span class="cp-queue-aqi" style="border-color: {cat_col}; color: {cat_col};">AQI {latest_aqi:.0f}</span>'
                f'</div>'
                f'<div class="cp-queue-station">{station}</div>'
                f'<div class="cp-queue-meta">{zone} · Priority score {prio_score:.1f}/100</div>'
                f'<div class="cp-queue-action">{action}</div>'
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
