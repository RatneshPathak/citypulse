"""
CityPulse: Mumbai — Reusable UI Components
HTML/Streamlit card components, KPI tiles, badges, and dossiers.
Presentation layer with native Material Symbols icons 
"""
from html import escape
import pandas as pd
import streamlit as st
from theme import COLORS, AQI_PALETTE, get_aqi_category_color, get_priority_tier
from icons import ICONS
from config import EVENT_NAME, TEAM_MEMBERS, DISCLAIMER_TEXT

def render_compact_banner():
    """Renders a concise, professional regulatory disclaimer banner."""
    st.markdown(
        f'<div style="background: rgba(245, 158, 11, 0.10); border: 1px solid rgba(245, 158, 11, 0.35); '
        f'border-radius: 8px; padding: 8px 14px; font-size: 0.80rem; color: #FBBF24; margin-bottom: 0.8rem; '
        f'display: flex; align-items: center; gap: 8px;">'
        f'<strong>DECISION-SUPPORT PROTOTYPE</strong>'
        f'<span style="color: {COLORS["text"]};">Designed for municipal planning and environmental inspection triage (BMC / MPCB). '
        f'This is a research prototype, not an official real-time warning system.</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_header(station_name: str, date_str: str, total_stations: int = 37):
    """Renders the executive command center header with status badges."""
    station = escape(station_name)
    date = escape(date_str)
    
    st.markdown(
        f'<div class="cp-cmd-header">'
        f'  <div class="cp-cmd-branding">'
        f'    <div class="cp-cmd-icon">'
        f'      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><path d="M3 21h18M5 21V7l8-4v18M13 21V11l6 3v7M8 10h1M8 14h1M8 18h1M16 16h1M16 19h1"/></svg>'
        f'    </div>'
        f'    <div class="cp-cmd-titles">'
        f'      <div class="cp-cmd-kicker">MUMBAI URBAN INTELLIGENCE · COMMAND CENTER</div>'
        f'      <h1 class="cp-cmd-name">CityPulse: Mumbai</h1>'
        f'      <p class="cp-cmd-tagline">Predictive Air Quality Prioritisation & Municipal Environmental Triage</p>'
        f'    </div>'
        f'  </div>'
        f'  <div class="cp-cmd-badges">'
        f'    <span class="cp-pill cp-pill-amber">Historical Demo · Decision Replay</span>'
        f'    <span class="cp-pill cp-pill-teal">Focus: {station}</span>'
        f'    <span class="cp-pill">As of {date}</span>'
        f'    <span class="cp-pill">{total_stations} Stations Monitored</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_data_status_bar(
    decision_date: str,
    target_date: str,
    reliability_label: str = "High",
    total_stations: int = 30,
    observation_range: str = "2021–2023",
    data_source: str = "CPCB / MPCB & ERA5",
):
    """
    Renders a transparent data-status bar providing explicit context:
    Dataset status, Observation period, Dashboard mode, Data source, Station reliability.
    """
    rel_pill_class = {
        "High": "cp-pill-green",
        "Medium": "cp-pill-amber",
        "Low": "cp-pill-red",
    }.get(reliability_label, "cp-pill-amber")

    st.markdown(
        f'<div class="cp-status-bar">'
        f'  <div class="cp-status-items">'
        f'    <div class="cp-status-item">'
        f'      <span class="cp-status-label">Dataset Status</span>'
        f'      <span class="cp-status-value"><span style="color: #FBBF24;">●</span> Historical</span>'
        f'    </div>'
        f'    <div class="cp-status-item">'
        f'      <span class="cp-status-label">Observation Period</span>'
        f'      <span class="cp-status-value">{escape(observation_range)}</span>'
        f'    </div>'
        f'    <div class="cp-status-item">'
        f'      <span class="cp-status-label">Dashboard Mode</span>'
        f'      <span class="cp-status-value">Decision Replay ({escape(decision_date)} → {escape(target_date)})</span>'
        f'    </div>'
        f'    <div class="cp-status-item">'
        f'      <span class="cp-status-label">Data Sources</span>'
        f'      <span class="cp-status-value">{escape(data_source)}</span>'
        f'    </div>'
        f'    <div class="cp-status-item">'
        f'      <span class="cp-status-label">Station Reliability</span>'
        f'      <span class="cp-status-value"><span class="cp-pill {rel_pill_class}" style="padding: 1px 7px; font-size: 0.70rem;">{escape(reliability_label)}</span></span>'
        f'    </div>'
        f'  </div>'
        f'  <div style="font-size: 0.76rem; color: {COLORS["text_muted"]}; display: flex; align-items: center; gap: 6px;">'
        f'    <span>Coverage: <strong>{total_stations} stations</strong> quality-screened</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_navigation_guide():
    """Navigation overview guide."""
    st.markdown(
        f'<div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin: 0.5rem 0 1rem;">'
        f'  <div style="background: {COLORS["surface"]}; border: 1px solid {COLORS["border"]}; border-radius: 8px; padding: 10px 12px;">'
        f'    <strong style="color: {COLORS["accent"]}; font-size: 0.80rem; display: block;">1. Overview</strong>'
        f'    <span style="color: {COLORS["text_muted"]}; font-size: 0.72rem;">Executive KPIs, map & action queue</span>'
        f'  </div>'
        f'  <div style="background: {COLORS["surface"]}; border: 1px solid {COLORS["border"]}; border-radius: 8px; padding: 10px 12px;">'
        f'    <strong style="color: #ffffff; font-size: 0.80rem; display: block;">2. Decision Center</strong>'
        f'    <span style="color: {COLORS["text_muted"]}; font-size: 0.72rem;">Rankings, what-if, routing & export</span>'
        f'  </div>'
        f'  <div style="background: {COLORS["surface"]}; border: 1px solid {COLORS["border"]}; border-radius: 8px; padding: 10px 12px;">'
        f'    <strong style="color: #ffffff; font-size: 0.80rem; display: block;">3. Air Quality Insights</strong>'
        f'    <span style="color: {COLORS["text_muted"]}; font-size: 0.72rem;">Longitudinal patterns & weather</span>'
        f'  </div>'
        f'  <div style="background: {COLORS["surface"]}; border: 1px solid {COLORS["border"]}; border-radius: 8px; padding: 10px 12px;">'
        f'    <strong style="color: #ffffff; font-size: 0.80rem; display: block;">4. Model Intelligence</strong>'
        f'    <span style="color: {COLORS["text_muted"]}; font-size: 0.72rem;">Forecast error, diagnostics & backtest</span>'
        f'  </div>'
        f'  <div style="background: {COLORS["surface"]}; border: 1px solid {COLORS["border"]}; border-radius: 8px; padding: 10px 12px;">'
        f'    <strong style="color: #ffffff; font-size: 0.80rem; display: block;">5. Citizen & Reports</strong>'
        f'    <span style="color: {COLORS["text_muted"]}; font-size: 0.72rem;">Public guide, live demo & audit</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_takeaway(text: str, highlight: str = "Key Decision Takeaway:"):
    """Renders a prominent, plain-language takeaway box at the top of a page."""
    st.info(f"**{highlight}** {text}", icon=":material/lightbulb:")

def render_kpi_card(
    label: str,
    value: str,
    subtext: str = "",
    color_accent: str | None = None,
    badge: str | None = None,
):
    """Renders a high-contrast command center KPI metric tile."""
    accent_bar = f"border-top-color: {color_accent};" if color_accent else f"border-top-color: {COLORS['accent']};"
    badge_html = f"<span class='cp-pill' style='font-size: 0.68rem; padding: 1px 6px;'>{escape(str(badge))}</span>" if badge else ""
    val_color = color_accent if color_accent else "#ffffff"

    html = (
        f'<div class="cp-kpi-card" style="{accent_bar}">'
        f'<div class="cp-kpi-label"><span>{escape(label)}</span>{badge_html}</div>'
        f'<div class="cp-kpi-val" style="color: {val_color};">{escape(str(value))}</div>'
        f'<div class="cp-kpi-sub">{escape(subtext)}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def render_action_strip(priority_df: pd.DataFrame, top_n: int = 5):
    """Renders readable inspection action cards for top priority zones."""
    st.markdown(f"##### {ICONS['action_queue']} Immediate Municipal Action Queue (Priority Zones)")
    top_rows = priority_df.head(top_n)
    if top_rows.empty:
        st.info("No priority zones are available for this replay date.")
        return

    cols = st.columns(min(3, len(top_rows)), gap="medium")
    for i, (_, row) in enumerate(top_rows.iterrows()):
        _, aqi_col = get_aqi_category_color(row["latest_aqi"])
        rank = int(row["rank"])
        tier_label, tier_col = get_priority_tier(rank, capacity_n=top_n)
        station = escape(str(row["station"]))
        latest_aqi = float(row["latest_aqi"])
        prio_score = float(row["priority_score"])
        zone = escape(str(row["zone"]))
        action = escape(str(row["recommended_action"]))

        with cols[i % len(cols)]:
            card_html = (
                f'<div class="cp-queue-card" style="border-top-color: {tier_col};">'
                f'  <div class="cp-queue-top">'
                f'    <span class="cp-queue-rank" style="color: {tier_col};">Priority #{rank} · {tier_label}</span>'
                f'    <span class="cp-pill" style="border-color: {aqi_col}; color: {aqi_col}; font-weight: 700;">AQI {latest_aqi:.0f}</span>'
                f'  </div>'
                f'  <div class="cp-queue-station">{station}</div>'
                f'  <div class="cp-queue-meta">{zone} • Priority Score {prio_score:.1f}/100</div>'
                f'  <div class="cp-queue-action" style="background: {COLORS["surface_raised"]}; border-radius: 6px; padding: 8px 10px; border: 1px solid {COLORS["border"]};">'
                f'    <strong style="color: #ffffff; font-size: 0.78rem; text-transform: uppercase;">Field Directive:</strong><br>'
                f'    {action}'
                f'  </div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

def render_ranked_summary(priority_df: pd.DataFrame, top_n: int = 5):
    """Renders a ranked zone summary explaining why each top zone was prioritized."""
    top_rows = priority_df.head(top_n)
    if top_rows.empty:
        return

    st.markdown(f"##### :material/summarize: Top {top_n} Priority Zones & Evidence Summary")
    
    summary_cards_html = []
    for _, row in top_rows.iterrows():
        rank = int(row["rank"])
        station = escape(str(row["station"]))
        zone = escape(str(row["zone"]))
        score = float(row["priority_score"])
        latest_aqi = float(row["latest_aqi"])
        prob_unhealthy = float(row.get("forecast_prob_unhealthy", 0.0)) * 100
        _, aqi_color = get_aqi_category_color(latest_aqi)
        tier_label, tier_color = get_priority_tier(rank, capacity_n=top_n)
        
        # Primary reason detection
        reasons = []
        if latest_aqi >= 200:
            reasons.append(f"Elevated AQI ({latest_aqi:.0f})")
        if prob_unhealthy >= 50:
            reasons.append(f"High Next-Day Risk ({prob_unhealthy:.0f}%)")
        if row.get("score_persistence", 0) > 40:
            reasons.append("Multi-day persistence shock")
        if row.get("score_vulnerability", 0) > 40:
            reasons.append("Corridor / industrial proximity")
        if not reasons:
            reasons.append("Cumulative multi-criteria exposure")
        
        reason_badges = "".join([f"<span class='cp-pill' style='font-size: 0.68rem; margin-right: 4px;'>{r}</span>" for r in reasons])

        item_html = (
            f'<div style="background: {COLORS["surface"]}; border: 1px solid {COLORS["border"]}; '
            f'border-left: 4px solid {tier_color}; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; '
            f'display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">'
            f'  <div>'
            f'    <div style="display: flex; align-items: center; gap: 8px;">'
            f'      <strong style="color: #ffffff; font-size: 0.95rem;">#{rank}. {station}</strong>'
            f'      <span style="color: {COLORS["text_muted"]}; font-size: 0.78rem;">({zone})</span>'
            f'    </div>'
            f'    <div style="margin-top: 5px;">{reason_badges}</div>'
            f'  </div>'
            f'  <div style="display: flex; align-items: center; gap: 14px;">'
            f'    <div style="text-align: right;">'
            f'      <div style="font-size: 0.70rem; color: {COLORS["text_muted"]}; text-transform: uppercase;">Priority Score</div>'
            f'      <div style="font-size: 1.15rem; font-weight: 700; color: {COLORS["accent"]};">{score:.1f}</div>'
            f'    </div>'
            f'    <div style="text-align: right;">'
            f'      <div style="font-size: 0.70rem; color: {COLORS["text_muted"]}; text-transform: uppercase;">Latest AQI</div>'
            f'      <div style="font-size: 1.15rem; font-weight: 700; color: {aqi_color};">{latest_aqi:.0f}</div>'
            f'    </div>'
            f'  </div>'
            f'</div>'
        )
        summary_cards_html.append(item_html)

    st.markdown("".join(summary_cards_html), unsafe_allow_html=True)

def render_action_dossier(st_data: dict, allocated: bool = True):
    """Renders the comprehensive action dossier for the selected zone."""
    cat_name, cat_col = get_aqi_category_color(st_data["latest_aqi"])
    status_pill = (
        f"<span class='cp-pill cp-pill-red' style='font-size: 0.78rem;'>PRIORITY ALLOCATED (Rank #{st_data['rank']})</span>"
        if allocated
        else f"<span class='cp-pill' style='font-size: 0.78rem;'>ROUTINE MONITORING (Rank #{st_data['rank']})</span>"
    )

    station = escape(str(st_data["station"]))
    action = escape(str(st_data["recommended_action"]))
    evidence = escape(str(st_data["evidence_basis"]))
    caveats = escape(str(st_data["action_caveats"]))
    surf_raised = COLORS["surface_raised"]
    border = COLORS["border"]

    dossier_html = (
        f'<div class="cp-action-dossier" style="border-left-color: {cat_col};">'
        f'  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">'
        f'    <h3 class="cp-action-title"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px; margin-right:6px; display:inline-block;"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>Action Protocol: {station}</h3>'
        f'    <div>{status_pill}</div>'
        f'  </div>'
        f'  <div class="cp-action-text">'
        f'    <span style="font-size: 0.95rem; font-weight: 700; color: #ffffff;">Recommended Municipal Intervention:</span>'
        f'    <div style="margin-top: 6px; font-size: 0.95rem; color: #f1f5f9; background: {surf_raised}; border: 1px solid {border}; border-radius: 8px; padding: 12px 16px; line-height: 1.5;">'
        f'      {action}'
        f'    </div>'
        f'  </div>'
        f'  <div class="cp-evidence-grid">'
        f'    <div><strong style="color: #ffffff;">Verifiable Evidence Basis:</strong><br><span style="line-height: 1.45;">{evidence}</span></div>'
        f'    <div><strong style="color: #ffffff;">Operational Caveats:</strong><br><span style="line-height: 1.45;">{caveats}</span></div>'
        f'  </div>'
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
    """Renders a data provenance card."""
    status_col = {"USED": "#10B981", "SUPPLEMENTARY": "#F59E0B"}.get(status, "#EF4444")
    surf = COLORS["surface"]
    border = COLORS["border"]
    muted = COLORS["text_muted"]
    text = COLORS["text"]

    card_html = (
        f'<div style="background: {surf}; border: 1px solid {border}; border-radius: 10px; padding: 16px 18px; margin-bottom: 12px;">'
        f'  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">'
        f'    <h4 style="margin: 0; color: #ffffff; font-size: 0.98rem; font-weight: 700;">{escape(name)}</h4>'
        f'    <div style="display: flex; gap: 6px;">'
        f'      <span class="cp-pill" style="font-size: 0.70rem;">{escape(licence)}</span>'
        f'      <span style="background: {status_col}22; border: 1px solid {status_col}; color: {status_col}; border-radius: 4px; padding: 2px 8px; font-size: 0.70rem; font-weight: 700;">{escape(status)}</span>'
        f'    </div>'
        f'  </div>'
        f'  <div style="font-size: 0.80rem; color: {muted}; margin-bottom: 8px;">'
        f'    <strong>Provider:</strong> {escape(provider)} • <strong>Accessed:</strong> {escape(access_date)}'
        f'  </div>'
        f'  <div style="font-size: 0.82rem; color: {text}; line-height: 1.4;">'
        f'    <strong>Fields / Usage:</strong> {escape(fields)}<br>'
        f'    <span style="color: {muted};">{escape(details)}</span>'
        f'  </div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

def render_footer():
    """Renders the persistent HackAMatch credit & data provenance footer."""
    footer_html = (
        f'<div class="cp-footer">'
        f'  <div class="cp-footer-primary">Built for <strong>{EVENT_NAME}</strong> by <strong>{TEAM_MEMBERS}</strong></div>'
        f'  <div class="cp-footer-secondary">{DISCLAIMER_TEXT}</div>'
        f'</div>'
    )
    st.markdown(footer_html, unsafe_allow_html=True)
