"""Streamlit view: Action and Solutions Library + searchable FAQ.

Content lives in knowledge_content.py. No external API, no chatbot.
"""
from knowledge_content import (
    ACTIONS, FAQ, NO_REF, REFERENCES, TIERS, faq_categories, search_faq,
)


def _ref_links(ref_ids):
    if not ref_ids:
        return NO_REF
    return "  \n".join(
        f"[{REFERENCES[r]['name']}]({REFERENCES[r]['url']})" for r in ref_ids if r in REFERENCES
    )


def render_action_library(st, default_tier=None):
    st.markdown("#### Action and Solutions Library")
    st.caption(
        "Reviewable suggestions, not automatic enforcement decisions. CityPulse cannot identify a pollution "
        "source from PM2.5 alone. Responsible roles are illustrative; confirm them against your own procedures."
    )
    options = ["All tiers"] + TIERS
    index = options.index(default_tier) if default_tier in options else 0
    tier = st.selectbox("Show suggestions relevant to heuristic tier", options, index=index, key="kh_tier")
    shown = [a for a in ACTIONS if tier == "All tiers" or tier in a["tiers"]]
    st.write(f"{len(shown)} suggestion(s)")
    for a in shown:
        with st.expander(a["name"]):
            st.markdown(f"**Applies to tiers:** {', '.join(a['tiers'])}")
            st.markdown(f"**Trigger or condition:** {a['trigger']}")
            st.markdown(f"**Suggested operational response:** {a['response']}")
            st.markdown(f"**Rationale:** {a['rationale']}")
            st.markdown(f"**Responsible stakeholder (illustrative):** {a['stakeholder']}")
            st.markdown(f"**Evidence or reference:**  \n{_ref_links(a['refs'])}")
            st.markdown(f"**Limitations and safeguards:** {a['limits']}")


def render_faq(st):
    st.markdown("#### Frequently asked questions")
    st.caption("Curated answers. Results are read from the Evidence panel, not repeated here.")
    c1, c2 = st.columns([2, 1])
    with c1:
        query = st.text_input("Search questions and answers", key="kh_query", placeholder="e.g. interval, sensor, AQI")
    with c2:
        cats = st.multiselect("Topic", faq_categories(), key="kh_cats")
    results = search_faq(query, cats)
    st.write(f"{len(results)} of {len(FAQ)} questions")
    if not results:
        st.info("No question matches. Try fewer or different words, or clear the topic filter.")
    for item in results:
        with st.expander(item["q"]):
            st.markdown(item["a"])
            st.caption(f"Topic: {item['category']}")


def render_references(st):
    with st.expander("References used on this page"):
        for r in REFERENCES.values():
            st.markdown(f"- [{r['name']}]({r['url']})  \n  {r['note']}")


def render_knowledge_hub(default_tier=None):
    import streamlit as st

    st.subheader("Action Centre and Knowledge Hub")
    st.caption(
        "Educational decision-support prototype built on public data. Not an official CPCB forecast "
        "or warning system."
    )
    t_actions, t_faq = st.tabs(["Action and Solutions Library", "FAQ"])
    with t_actions:
        render_action_library(st, default_tier)
    with t_faq:
        render_faq(st)
    render_references(st)
