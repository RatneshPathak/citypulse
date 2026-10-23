"""
CityPulse Decision Support Modules

Provides decision-support tools for municipal environmental planning:
- whatif: Policy weight sensitivity and rank stability simulation
- routing: Inspection route planning with nearest-neighbor TSP
- briefing: Printable weekly briefing export (HTML/PDF)
- validation: Honest validation metrics and prioritization backtest
"""

from .whatif import compute_rank_stability, compute_rank_delta
from .routing import compute_inspection_route, haversine_distance
from .briefing import generate_briefing_html, render_briefing_export_ui
from .validation import (
    backtest_prioritization_strategy,
    compute_interval_coverage,
    compute_skill_scores,
    render_validation_panel
)

__all__ = [
    "compute_rank_stability",
    "compute_rank_delta",
    "compute_inspection_route",
    "haversine_distance",
    "generate_briefing_html",
    "render_briefing_export_ui",
    "backtest_prioritization_strategy",
    "compute_interval_coverage",
    "compute_skill_scores",
    "render_validation_panel",
]
