"""
CityPulse: Mumbai — Guided Demo Mode

Step-by-step walkthrough for live presentations and judging sessions.
"""
import streamlit as st
from typing import List, Dict


DEMO_STEPS = [
    {
        "number": 1,
        "title": "The Problem",
        "icon": ":material/crisis_alert:",
        "content": """
**Mumbai's air quality challenge:**
- 36 monitoring stations across Mumbai Metropolitan Region
- 600K+ hourly AQI records (2021-2023)
- Limited municipal resources: typically 5-10 inspection teams
- **Decision challenge:** *Which zones need attention THIS WEEK?*

**Key constraint:** Cannot inspect all zones — must prioritize intelligently.
        """,
        "metric_label": "Challenge",
        "metric_value": "Finite Resources",
        "metric_delta": "5-10 teams for 36 zones"
    },
    {
        "number": 2,
        "title": "The Data",
        "icon": ":material/database:",
        "content": """
**100% free, open, verifiable data:**
- ✅ CPCB/MPCB air quality (597,912 hourly records)
- ✅ Open-Meteo weather (26,280 hourly observations)
- ✅ OpenStreetMap land use context
- ❌ **NO** paid APIs, API keys, or synthetic data

**Data quality:** 18-hour validity rule, sensor-stuck filtering, gap interpolation.
        """,
        "metric_label": "Data Points",
        "metric_value": "624K+",
        "metric_delta": "All open & verified"
    },
    {
        "number": 3,
        "title": "Multi-Criteria Prioritization",
        "icon": ":material/balance:",
        "content": """
**Priority Score combines 5 evidence streams:**
1. **Recent Exposure** (7-day mean AQI)
2. **Persistence Shock** (days > 150 AQI)
3. **Trend Acceleration** (rate of worsening)
4. **Forecast Risk** (probability AQI > 200)
5. **Vulnerability Context** (highway corridors, industrial zones)

Each component is normalized 0-100, weighted by policy, combined → Priority Score.
        """,
        "metric_label": "Ranking Method",
        "metric_value": "Multi-Criteria",
        "metric_delta": "5 evidence streams"
    },
    {
        "number": 4,
        "title": "What-If Policy Simulator",
        "icon": ":material/tune:",
        "content": """
**Interactive weight adjustment:**
- Adjust weights in sidebar → see rankings update instantly
- Monte Carlo stability: which zones robust to policy changes?
- Rank movement visualization with arrows

**Use case:** Policy maker wants exposure-heavy vs forecast-heavy strategy.
        """,
        "metric_label": "Simulations",
        "metric_value": "500 runs",
        "metric_delta": "±30% perturbation"
    },
    {
        "number": 5,
        "title": "Route Planner",
        "icon": ":material/route:",
        "content": """
**Practical inspection logistics:**
- Select top-N priority zones
- Compute nearest-neighbor tour (haversine distance)
- Numbered stops on map, total distance
- **Honest disclaimer:** straight-line, not road routing

**Output:** Printable route schedule with distances.
        """,
        "metric_label": "Route Algorithm",
        "metric_value": "Nearest-Neighbor",
        "metric_delta": "Greedy heuristic"
    },
    {
        "number": 6,
        "title": "Validation & Honesty",
        "icon": ":material/verified:",
        "content": """
**Rigorous backtest on 2023 holdout:**
- Priority strategy hit rate: **+XX% vs random selection**
- Model MAE vs persistence baseline: shown honestly
- 80% intervals: actual coverage reported (under/over)
- **We show where it doesn't work**

**Technical judges:** This is the validation section you want to see.
        """,
        "metric_label": "Backtest Period",
        "metric_value": "2023",
        "metric_delta": "Chronological holdout"
    },
    {
        "number": 7,
        "title": "Printable Briefing",
        "icon": ":material/description:",
        "content": """
**One-click weekly briefing export:**
- Top-5 zones, recommended actions, evidence basis
- Policy weights used, data as-of date
- Data attribution footer
- Downloads as HTML (always) + PDF (if library available)

**This is the artifact an inspector carries to the field.**
        """,
        "metric_label": "Export Format",
        "metric_value": "HTML + PDF",
        "metric_delta": "Print-ready"
    },
    {
        "number": 8,
        "title": "Impact & Next Steps",
        "icon": ":material/rocket_launch:",
        "content": """
**Impact potential (computed from data):**
- Top-5 zones account for **XX%** of high-AQI station-days
- Concentrating resources → measurable efficiency gain
- **NOT claiming lives saved** — that requires health outcome data

**Future work:**
- Live CPCB API integration
- Satellite AOD data for better forecasts
- SMS/WhatsApp alerts for citizens
- Multi-city deployment (Delhi, Pune, Kolkata)
        """,
        "metric_label": "Next Milestone",
        "metric_value": "Live Integration",
        "metric_delta": "CPCB real-time API"
    }
]


def render_guided_demo():
    """
    Renders an interactive guided demo with step-by-step walkthrough.
    """
    st.markdown("### 🎬 Guided Demo Mode")
    st.caption("**For judges & presentations:** Step through the CityPulse story in 90 seconds")
    
    # Initialize demo state
    if "demo_step" not in st.session_state:
        st.session_state.demo_step = 0
    
    # Progress bar
    progress = (st.session_state.demo_step + 1) / len(DEMO_STEPS)
    st.progress(progress, text=f"Step {st.session_state.demo_step + 1} of {len(DEMO_STEPS)}")
    
    # Navigation buttons
    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 1, 1, 2])
    
    with col_nav1:
        if st.button("⏮️ First", use_container_width=True, disabled=st.session_state.demo_step == 0):
            st.session_state.demo_step = 0
            st.rerun()
    
    with col_nav2:
        if st.button("◀️ Previous", use_container_width=True, disabled=st.session_state.demo_step == 0):
            st.session_state.demo_step -= 1
            st.rerun()
    
    with col_nav3:
        if st.button("Next ▶️", use_container_width=True, type="primary", disabled=st.session_state.demo_step >= len(DEMO_STEPS) - 1):
            st.session_state.demo_step += 1
            st.rerun()
    
    with col_nav4:
        if st.button("⏭️ Jump to Validation (Step 6)", use_container_width=True):
            st.session_state.demo_step = 5
            st.rerun()
    
    # Current step content
    st.markdown("---")
    step = DEMO_STEPS[st.session_state.demo_step]
    
    col_step1, col_step2 = st.columns([3, 1])
    
    with col_step1:
        st.markdown(f"## {step['icon']} Step {step['number']}: {step['title']}")
        st.markdown(step["content"])
    
    with col_step2:
        st.metric(
            label=step["metric_label"],
            value=step["metric_value"],
            delta=step["metric_delta"]
        )
    
    # Auto-advance option
    st.markdown("---")
    auto_advance = st.checkbox("🔄 Auto-advance every 15 seconds", value=False, help="Useful for automated demos")
    
    if auto_advance:
        import time
        st.info("Demo will advance automatically. Click 'Previous' to pause.", icon=":material/play_circle:")
        if st.session_state.demo_step < len(DEMO_STEPS) - 1:
            time.sleep(15)
            st.session_state.demo_step += 1
            st.rerun()
    
    # Quick jump menu
    with st.expander("📑 Jump to Step"):
        for i, s in enumerate(DEMO_STEPS):
            if st.button(f"{s['number']}. {s['title']}", key=f"jump_{i}", use_container_width=True):
                st.session_state.demo_step = i
                st.rerun()
