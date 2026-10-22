"""STANDALONE INTEGRATION ENTRY POINT (not the teammates' main app.py).

Run from the repository root:   streamlit run src/app_standalone.py

It exists because the project ZIP contained no app.py. It shows the three new views as tabs.
To add them to the existing app instead, call these from its own tabs (see INTEGRATION.md):
    from action_centre import render_action_centre
    from latest_check import render_latest_check
    from knowledge_hub import render_knowledge_hub
"""
import sys
from pathlib import Path

import streamlit as st

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from action_centre import render_action_centre  # noqa: E402
from knowledge_hub import render_knowledge_hub  # noqa: E402
from latest_check import render_latest_check  # noqa: E402

st.set_page_config(page_title="CityPulse: Predict. Explain. Act.", layout="wide")
st.title("CityPulse: Predict. Explain. Act.")
st.caption("Mumbai air quality decision support for four monitoring stations. Educational prototype. "
           "Persistence estimates, heuristic tiers, advisory actions. Not an official warning system.")

tab_action, tab_latest, tab_hub = st.tabs(["Action Centre", "Latest data check", "Knowledge Hub"])
with tab_action:
    render_action_centre(ROOT)
with tab_latest:
    render_latest_check(ROOT)
with tab_hub:
    render_knowledge_hub()
