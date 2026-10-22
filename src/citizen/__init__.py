"""
CityPulse Citizen-Facing Features

Simplified public view with health guidance and shareable cards.
"""

from .citizen_view import render_citizen_mode, generate_aqi_card_html

__all__ = ["render_citizen_mode", "generate_aqi_card_html"]
