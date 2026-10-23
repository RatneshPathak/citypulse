"""
CityPulse: Mumbai — Global Configuration
Central configuration for event branding, team credits, project metadata,
and graceful secret/environment variable management for deployment.
"""
import os
from typing import Optional

EVENT_NAME = "HackAMatch 1.0"
TEAM_MEMBERS = "Ratnesh, Rishi & Shreya"
APP_NAME = "CityPulse: Mumbai"
APP_TAGLINE = "Air Quality Prioritisation & Decision Support"
APP_VERSION = "2.1"

DATA_ATTRIBUTION = "CPCB / Open-Meteo / OpenStreetMap contributors (ODbL)"

DISCLAIMER_TEXT = (
    f"{APP_NAME} is a prototype, not an official warning system. "
    f"Data: {DATA_ATTRIBUTION}. See DATA_SOURCES.md for licences and access dates."
)

def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Safely retrieves a secret from Streamlit secrets (st.secrets) with
    fallback to OS environment variables. Never raises KeyError.

    Parameters
    ----------
    key : str
        The secret/environment variable name (e.g. 'DATA_GOV_IN_KEY').
    default : Optional[str]
        Fallback value if the secret is not found.

    Returns
    -------
    Optional[str]
        The resolved secret string, or default.
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            val = st.secrets[key]
            if val is not None and str(val).strip():
                return str(val).strip()
    except Exception:
        pass

    env_val = os.environ.get(key)
    if env_val is not None and env_val.strip():
        return env_val.strip()

    return default
