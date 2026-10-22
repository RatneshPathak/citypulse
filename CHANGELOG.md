# UI/UX & Data-Visualization Changelog — CityPulse: Mumbai

Release: v2.1 (Design System & Presentation-Layer Redesign)  
Focus: Modernizing the decision-support dashboard for municipal inspectors (BMC / MPCB role) into a polished, executive-ready interface.

---

## 1. Design System & Theming (`theme.py`)
- **Dark-First Architectural Palette:**
  - Canvas background: `#0B1220` (Deep Navy)
  - Card Surface: `#111A2B` (Subtle 1px border `#24324D`, 14px radius)
  - Surface Raised: `#172238` (Popovers, chip badges)
  - Primary Accent: `#4F8CFF` (Electric Blue) with `#00D2FF` secondary
  - High-contrast text `#E6EDF7` with muted metadata `#8FA1BD` (WCAG AA compliant)
- **Universal Semantic CPCB AQI Palette:**
  - Defined once in `AQI_PALETTE` and shared strictly across all maps, scatter points, bar charts, pills, and dataframes:
    - Good: `#2ECC71`
    - Satisfactory: `#A3D86B`
    - Moderate: `#F5C542`
    - Poor: `#F08A3C`
    - Very Poor: `#E5484D`
    - Severe: `#8E2BA8`
- **Global Plotly Template (`citypulse_dark`):**
  - Fully transparent paper and plot backgrounds (`rgba(0,0,0,0)`).
  - Micro-gridlines (`alpha 0.08`), clean axis spines, zero chart junk.
  - Custom dark hovercards styled with `#172238` background, `#4F8CFF` accent border, and `Inter` typography.
- **CSS Component Layer:**
  - Injected Google Font `Inter` (weights 300 to 700).
  - Pill-style tab navigation with electric blue active tab indicator and hover transitions.
  - Hidden Streamlit default headers/footers for a standalone software feel.

---

## 2. Global Layout & Components (`components.py`)
- **Compact Hero Header:**
  - Replaced the bulky banner with a streamlined hero containing title, municipal context, and three real-time chip badges: Active Network Count, Data Freshness Date, and Current Focused Station.
- **Concise Disclaimer:**
  - Shortened the prototype warning banner by ~50% into a single-line compact amber banner (`#F5C542`).
- **Dynamic Policy Weight Controls (Sidebar):**
  - Added grouped sections ("Location Target" and "Prioritisation Policy Weights").
  - Added live "Total Weight = 1.00" balance indicator (turns amber with auto-normalization alert if $\sum w \ne 1.0$).
  - Added "🔄 Reset to Recommended Defaults" button.
  - Added descriptive `help=` tooltips on all 5 weight sliders and the inspection capacity slider.
- **Takeaway-First Architecture:**
  - Every single tab now leads with an executive "So what?" plain-language insight box with bold highlights.
- **Top KPI Cards:**
  - Uniform 4-tile metric rows at the top of each tab with label, large value, small subtext/delta, and category-colored left accent border.

---

## 3. Tab-by-Tab Visual & Chart Enhancements (`charts.py` & `app.py`)

### Tab 1: Risk Prioritisation (ACT)
- **Leaderboard Upgrade:**
  - Replaced standard table with interactive `st.dataframe` using `st.column_config`:
    - Hidden row index.
    - `Priority Score` rendered as a gradient `ProgressColumn` (0–100).
    - Status pills: `🔴 INSPECT` for zones within capacity $N$, `⚪ ROUTINE` for others.
    - Category column styled with CPCB classes.
- **Spatial Map Redesign:**
  - Switched to token-free `carto-darkmatter` dark basemap.
  - Dynamic marker size based on latest AQI, colored by Priority Score (`YlOrRd`).
  - Active station highlighted with a vibrant cyan double-ring.
  - Labels restricted cleanly to top-5 priority zones to eliminate text collision.
- **Why is this Ranked #1? Score Decomposition:**
  - Added horizontal stacked bar chart showing the exact weighted point contribution from Exposure, Persistence, Trend, Forecast, and Vulnerability.
- **Top Action Strip:**
  - Added a horizontal 5-card operational preview showing immediate next steps.
- **Action Dossier:**
  - Redesigned into a dark card with category-colored border, highlighted municipal action, and split evidence/caveat grid.

### Tab 2: Discover and Patterns
- **Longitudinal Time Series:**
  - CPCB regulatory bands drawn as subtle background shading with labels pinned to the **far right edge**, avoiding data collisions.
  - Thin daily actual line with thick 7-day rolling trend.
  - Gaps rendered honestly (`connectgaps=False`).
  - Quick-range selector buttons (`1M`, `6M`, `1Y`, `All Data`) plus date range slider.
  - Annotated peak shock episode.
- **Category Distribution Strip:**
  - Added 100% horizontal stacked bar showing exact percentage of monitoring days spent in each CPCB category.
- **Seasonal & Weekly Bar Profiles:**
  - Monthly profile with shaded monsoon washout period.
  - Day-of-week profile showing weekday traffic vs weekend respite.

### Tab 3: Weather & Dispersion
- **Wind vs AQI Scatter:**
  - Ordered legend from Good to Severe matching the CPCB palette.
  - Reduced overplotting with 0.6 opacity and 6px marker radius.
  - Shaded stagnant wind zone (< 6 km/h) with alert annotation.
  - Added binned-median trendline.
- **Diverging Correlation Chart:**
  - Replaced plain table with a horizontal diverging bar chart (blue negative, red positive), sorted by absolute strength $|r|$.
  - Direct bar text labeling.
  - Generated dynamic plain-language summary text assessing driver strength (weak/moderate/strong).
- **Polar Wind Rose:**
  - Added 8-octant polar bar chart showing mean AQI by wind direction, demonstrating clean maritime SW/W winds vs continental NE winds.

### Tab 4: Forecast & Risk Calibration
- **Plain-Language Reframing:**
  - Removed internal jargon ("Hard Rule 5 Compliance") in favor of an honest 4-card metric row comparing Persistence Baseline (19.4) vs Model Forecast (20.2), 80% range, and holdout MAE.
- **Holdout Validation Chart:**
  - Solid light actual line, dashed electric blue forecast, smooth 80% prediction interval (`fill='toself'`).
  - Regulatory threshold (AQI 200) labeled directly on the dotted red line.
  - Exceedances highlighted with small red scatter markers.
- **Diagnostic Curves:**
  - Added Reliability Diagram (Calibration Curve) with diagonal perfect-calibration reference.
  - Added Parity Scatter ($y=x$) with empirical interval coverage readout (74.2%).
- **Anomaly Inspection Table:**
  - Formatted dates as `YYYY-MM-DD`, residual error to 1 decimal, with clear directional badges (`🔵 Over-predicted` / `🔴 Under-predicted`).

### Tab 5: Data Provenance & Methods
- **Modular Data Source Cards:**
  - Replaced raw markdown with structured source cards detailing provider, licence badge, status chip (`USED` / `REJECTED`), fields, and hygiene notes.
- **Clean Architecture Pipeline:**
  - Visual ASCII/Mermaid flow showing ingestion, cleaning, feature engineering, modeling, and prioritization.
- **Interactive Expansion:**
  - Collapsible expander detailing specific missing data feeds (satellite AOD, hyper-local sensor meshes, traffic speed telemetry) required to beat persistence in all seasons.


---

## 2. Hackathon Feature Release (v2.5 — October 23, 2026)

### 🚀 Major Decision Support Suite

**Summary:** Complete enhancement with decision support tools, citizen mode, and rigorous validation for HackAMatch 1.0 final judging.

### Added Features

#### Decision Support (Priority A)
- **A1. What-If Policy Simulator** ✅ (Tab 2)
  - Interactive weight adjustment with real-time rank updates
  - Monte Carlo stability: 500 runs, ±30% perturbations
  - Probability heatmaps and rank range plots
  - ~150 LOC in `src/decision/whatif.py`

- **A2. Inspection Route Planner** ✅ (Tab 3)
  - Nearest-neighbor TSP with haversine distance
  - Interactive map with numbered stops
  - Route table with leg/cumulative distances
  - ~200 LOC in `src/decision/routing.py`

- **A3. Weekly Briefing Export** ✅ (Tab 4)
  - One-click HTML/PDF printable briefings
  - Top-N zones, actions, evidence, attribution
  - Clean print CSS (A4, page-break-inside: avoid)
  - ~250 LOC in `src/decision/briefing.py`

- **A4. Enhanced Action Recommendations** ✅ (Tab 1)
  - Rule-based, transparent (no black-box AI)
  - Context-aware: traffic, industrial, construction
  - Evidence basis + operational caveats

#### Explainability & Trust (Priority B)
- **B1. Score Breakdown Explainer** ✅ (Tab 1)
  - Waterfall chart: sub-scores, weights, contributions
  - ~50 LOC in `charts.py::plot_score_breakdown()`

- **B3. Honest Validation Panel** ✅ (Tab 8)
  - Priority strategy backtest (+33% lift vs random)
  - Model vs baseline (MAE: model 20.3, persistence 19.4)
  - Interval coverage (74.1% actual vs 80% nominal)
  - ~200 LOC in `src/decision/validation.py`

#### Citizen Features (Priority D)
- **D1. Citizen View** ✅ (Tab 9)
  - Simplified health guidance (CPCB categories)
  - Big AQI display with color gradient
  - 7-day forecast with uncertainty
  - ~300 LOC in `src/citizen/citizen_view.py`

- **D2. Shareable AQI Cards** ✅ (Tab 9)
  - HTML cards for WhatsApp/Twitter
  - Trend indicators, responsive design
  - ~100 LOC

#### Demo & Presentation (Priority E)
- **E1. Guided Demo Mode** ✅ (Tab 10)
  - 8-step interactive walkthrough (60-90s)
  - Auto-advance option for automated demos
  - Progress bar, quick jump menu
  - ~180 LOC in `src/demo/guided_demo.py`

### Testing & Documentation
- **10 new unit tests** in `tests/test_decision_features.py` (all passing)
- **FEATURES.md**: Complete inventory with status (A1-E3)
- **DEMO_SCRIPT_V2.md**: 3-minute live demo script
- **PITCH_OUTLINE.md**: 5-slide pitch deck outline
- **Updated README.md**: Feature highlights, new structure

### UI/UX Changes
- **11 tabs** (up from 5):
  1. Priority Rankings
  2. What-If Simulator
  3. Route Planner
  4. Briefing Export
  5. Historical Patterns
  6. Weather Analysis
  7. Forecast Performance
  8. Validation & Backtest
  9. Citizen View
  10. Guided Demo
  11. Data & Methods

- **Sidebar additions**:
  - Resource Budget slider (1-15 teams)
  - Citizen Mode toggle
  - Weight reset button

### Performance Optimizations
- Heavy caching on Monte Carlo (500 runs)
- Route computation cached
- Backtest cached by parameters

### Known Limitations
1. Route distances are straight-line (not road routing)
2. PDF export requires optional libraries
3. Model doesn't beat persistence (reported honestly)
4. Intervals undercover (74.1% vs 80% nominal)

**Total New Code:** ~1,590 lines across 8 new modules  
**Tests:** 10 tests, 100% passing  
**Build Time:** ~72 hours (Oct 20-23, 2026)  
**Status:** READY FOR JUDGING ✅
