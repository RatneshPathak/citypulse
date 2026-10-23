# CityPulse: Mumbai — Feature Inventory

**Complete list of decision-support features built for HackAMatch 1.0**

---

## ✅ DECISION FEATURES (Priority A)

### A1. What-If Policy Simulator ✅ COMPLETE
**Status:** Fully implemented with interactive UI

**Capabilities:**
- Interactive weight adjustment in sidebar
- Real-time rank recomputation as weights change
- Rank movement visualization with arrows (↑ improved, ↓ worsened)
- **Rank Stability Monte Carlo**: 500-run simulation with ±30% perturbations
- Probability heatmap: which zones are "robust" to weight changes
- Rank range plots: visualize stability vs volatility
- Set/reset baseline for comparison

**Technical Details:**
- Cached computation for performance (`@st.cache_data`)
- NumPy random seed fixed for reproducibility
- Perturbations normalized to maintain valid weight distributions

**Location:** Tab 2 ("What-If Simulator"), `src/decision/whatif.py`

---

### A2. Inspection Route Planner ✅ COMPLETE
**Status:** Fully implemented with map visualization

**Capabilities:**
- Nearest-neighbor TSP heuristic for top-N zones
- Haversine distance calculation (straight-line, not road routing)
- Starting point selector (defaults to highest priority)
- Interactive map with numbered stops and route line
- Detailed route table with leg distances and cumulative totals
- **Honest disclaimer**: clearly states straight-line distance limitation

**Technical Details:**
- Greedy nearest-neighbor algorithm
- Earth radius = 6371 km
- Total distance and stop-by-stop breakdown
- Color-coded markers by AQI category

**Location:** Tab 3 ("Route Planner"), `src/decision/routing.py`

---

### A3. Weekly Briefing Export ✅ COMPLETE
**Status:** HTML always; PDF if library available

**Capabilities:**
- One-click generate printable one-page briefing
- Includes: top-N zones, AQI categories, recommended actions, evidence basis
- Policy weights table (transparency)
- Data attribution footer (CPCB, Open-Meteo, OSM)
- Generation timestamp and data "as of" date
- HTML download (always available)
- PDF export (if `weasyprint` or `xhtml2pdf` installed)

**Technical Details:**
- Clean print-friendly CSS (A4 size, readable fonts)
- Color-coded by AQI category
- Page-break-inside: avoid for cards
- Fallback gracefully if PDF libraries missing

**Location:** Tab 4 ("Briefing Export"), `src/decision/briefing.py`

---

### A4. Action Recommendations ✅ ENHANCED
**Status:** Rule-based, transparent, already in prioritization engine

**Capabilities:**
- Explicit rule-based recommendations (NO black-box AI)
- Context-aware: traffic corridors, industrial zones, landfills, construction
- Shows the rule that fired (e.g., "PM10-dominant + construction within 1.5km")
- Action cards in Tab 1 show truncated version
- Full "Action Dossier" with evidence and caveats

**Technical Details:**
- Rules in `src/models/prioritization.py::generate_action_recommendation()`
- Matches environment type to intervention strategy
- Includes operational caveats (e.g., "Station measures background, not source")

**Location:** Tab 1 (Action Dossier), `src/models/prioritization.py`

---

## ✅ EXPLAINABILITY & TRUST (Priority B)

### B1. Why-This-Station Explainer ✅ COMPLETE
**Status:** Waterfall chart + plain language

**Capabilities:**
- Stacked horizontal bar chart showing score contribution breakdown
- Each component shows: raw sub-score, weight, and points added
- Hover tooltips with detailed breakdown
- Colors distinguish the 5 criteria
- Plain-language interpretation (can be enhanced with narrative generation)

**Location:** Tab 1 (Score Breakdown chart), `charts.py::plot_score_breakdown()`

---

### B2. Model Explainability ⚠️ PLACEHOLDER
**Status:** Partial — feature importance available, needs visualization

**What's needed:**
- Extract `feature_importances_` from trained GradientBoostingRegressor
- Create bar chart of top 15 features
- Add permutation importance as alternative
- Annotate with plain-language explanations (e.g., "wind_speed_mean" → "Low wind traps pollutants")

**Recommendation:** Add to Tab 7 ("Forecast Performance") as subsection

---

### B3. Honest Validation Panel ✅ COMPLETE
**Status:** Fully implemented with backtest

**Capabilities:**
- **Priority Strategy Backtest**: simulates weekly inspections on 2023 holdout
  - Measures: "Top-N zones had AQI > 150 what % of time?"
  - Compares vs random selection baseline
  - Reports lift (e.g., "+27% vs random")
- **Model vs Baseline**: MAE, RMSE, skill score
- **Interval Coverage**: 80% nominal vs actual coverage
- **Honest Findings**: separate columns for "What Works" vs "Where We're Honest"
- Interpretation section for judges

**Technical Details:**
- Chronological weekly windows (no data leakage)
- Backtest uses only past data to rank, checks future outcomes
- Configurable threshold (default: AQI > 150)

**Location:** Tab 8 ("Validation & Backtest"), `src/decision/validation.py`

---

## ✅ EQUITY & CONTEXT (Priority C)

### C1. Vulnerability Layer ⚠️ PARTIAL
**Status:** Context available, needs OSM facility count

**What exists:**
- `env_type` field captures highway corridors, industrial zones
- Used in vulnerability score component

**What's needed:**
- Count OSM facilities (hospitals, schools, elderly care) within 2km buffer
- Add as optional map layer
- Include in explainer as "population-sensitivity proxy"

**Recommendation:** Add to Tab 1 as expandable section

---

### C2. Compare Stations ⚠️ FUTURE
**Status:** Not yet implemented

**Design:**
- Multiselect: choose 2-3 stations
- Side-by-side KPIs: mean AQI, category distribution, seasonality
- Overlaid time series chart
- Rank comparison in leaderboard

**Recommendation:** Add as Tab 1.5 or sidebar feature

---

### C3. Seasonal Insight Cards ⚠️ FUTURE
**Status:** Patterns visible in charts, not auto-detected

**What exists:**
- Seasonal profile chart shows monsoon washout vs winter stagnation
- Visual patterns clear

**What's needed:**
- Auto-detect recurring patterns (e.g., post-Diwali spike detection)
- Generate insight cards: "Monsoon months (Jun-Sep) average 63.9 AQI"

**Recommendation:** Add to Tab 5 ("Historical Patterns")

---

## ✅ CITIZEN-FACING MODE (Priority D)

### D1. Citizen View Toggle ✅ COMPLETE
**Status:** Fully implemented in Tab 9

**Capabilities:**
- Simplified plain-language view
- Big AQI display with color-coded category
- Health guidance by CPCB category (official guidelines)
- Separate guidance for sensitive groups (children, elderly, respiratory conditions)
- 7-day forecast with uncertainty range
- Health protection tips (masks, outdoor exercise, air purifiers)
- **Disclaimer**: clearly states not medical advice

**Technical Details:**
- CPCB health statement categories hardcoded from official guidelines
- No medical claims — only CPCB-approved guidance
- Cautious wording ("consider limiting" not "do not")

**Location:** Tab 9 ("Citizen View"), `src/citizen/citizen_view.py`

---

### D2. Shareable AQI Card ✅ COMPLETE
**Status:** HTML card generation with download

**Capabilities:**
- Clean, visual AQI card with station name, value, category
- Trend indicator (📈 worsening, 📉 improving, ➡️ stable)
- Date stamp and data attribution
- Downloads as standalone HTML (can be screenshotted for WhatsApp/Twitter)
- Mobile-friendly responsive design

**Location:** Tab 9 ("Citizen View"), `src/citizen/citizen_view.py::generate_aqi_card_html()`

---

## ✅ DEMO & PITCH POLISH (Priority E)

### E1. Guided Demo Mode ✅ COMPLETE
**Status:** 8-step interactive walkthrough

**Capabilities:**
- Step-by-step presentation mode (60-90 seconds)
- Navigation: Previous, Next, Jump to Step, Jump to Validation
- Progress bar shows completion
- Each step has: title, icon, content, metric card
- **Auto-advance option**: 15-second timer for hands-free demos
- Quick jump menu to any step

**Steps:**
1. The Problem (finite resources, 36 zones)
2. The Data (100% free & open)
3. Multi-Criteria Prioritization (5 components)
4. What-If Policy Simulator
5. Route Planner
6. Validation & Honesty (backtest results)
7. Printable Briefing
8. Impact & Next Steps

**Location:** Tab 10 ("Guided Demo"), `src/demo/guided_demo.py`

---

### E2. Impact Framing ⚠️ PARTIAL
**Status:** Framework exists, needs real computation

**What's needed:**
- Compute: "Top-5 zones account for X% of high-AQI station-days"
- Show resource concentration efficiency
- **NO HEALTH CLAIMS** — only exposure coverage

**Recommendation:** Add to Tab 1 or Demo as metric card

---

### E3. About / Architecture View ✅ PARTIAL
**Status:** Architecture diagram in Tab 11, needs enhancement

**What exists:**
- ASCII pipeline diagram (Sources → QC → Features → Models → Actions)
- Data provenance cards with licenses
- "What data would beat persistence?" section

**What's needed:**
- Tech stack table (Python, Streamlit, Plotly, Scikit-Learn, Pandas)
- Limitations section (monitoring gaps, no health outcomes)
- Future work roadmap (live API, SMS alerts, multi-city)

**Location:** Tab 11 ("Data & Methods")

---

## 📊 FEATURE SUMMARY

| Priority | Feature | Status | Tab | Lines of Code |
|----------|---------|--------|-----|---------------|
| A1 | What-If Simulator | ✅ Complete | Tab 2 | ~150 |
| A2 | Route Planner | ✅ Complete | Tab 3 | ~200 |
| A3 | Briefing Export | ✅ Complete | Tab 4 | ~250 |
| A4 | Action Recommendations | ✅ Enhanced | Tab 1 | ~80 |
| B1 | Score Explainer | ✅ Complete | Tab 1 | ~50 |
| B2 | Model Explainability | ⚠️ Partial | Tab 7 | ~0 |
| B3 | Validation Panel | ✅ Complete | Tab 8 | ~200 |
| C1 | Vulnerability Layer | ⚠️ Partial | Tab 1 | ~30 |
| C2 | Compare Stations | ⚠️ Future | - | ~0 |
| C3 | Seasonal Insights | ⚠️ Future | Tab 5 | ~0 |
| D1 | Citizen View | ✅ Complete | Tab 9 | ~300 |
| D2 | Shareable Cards | ✅ Complete | Tab 9 | ~100 |
| E1 | Guided Demo | ✅ Complete | Tab 10 | ~180 |
| E2 | Impact Framing | ⚠️ Partial | - | ~0 |
| E3 | Architecture View | ✅ Partial | Tab 11 | ~50 |

**Total New Code:** ~1,590 lines across decision, citizen, demo modules

---

## 🧪 TESTING STATUS

### Unit Tests ✅ COMPLETE
- `tests/test_decision_features.py`: 10 tests, all passing
  - Priority scoring bounds and validity
  - Haversine distance calculations
  - Route planning logic
  - What-if rank delta computation
  - Interval coverage bounds

### Integration Tests ⚠️ RECOMMENDED
- End-to-end flow: weights → priority → route → briefing
- Citizen view rendering with missing data
- Demo mode navigation

---

## 🎯 JUDGE-FRIENDLY HIGHLIGHTS

**For Technical Judges:**
- Tab 8: Honest validation with backtest lift calculation
- Tab 2: Monte Carlo stability analysis (500 runs)
- Tab 4: Reproducible briefing with data attribution
- Tests: `pytest tests/test_decision_features.py -v`

**For Product Judges:**
- Tab 10: Guided demo (full story in 90 seconds)
- Tab 3: Route planner with practical distance estimates
- Tab 9: Citizen-friendly health guidance

**For Design Judges:**
- Consistent Material Symbols icons throughout
- Color-blind-safe palettes (never red/green alone)
- Dark theme with high contrast (WCAG AA compliant)

---

## 📝 ASSUMPTIONS & LIMITATIONS

1. **Route distances are straight-line:** Real road routing requires paid APIs (Google Maps, Mapbox). We use haversine distance with clear disclaimer.

2. **PDF export optional:** Requires `weasyprint` or `xhtml2pdf`. HTML always available as fallback.

3. **Citizen health guidance:** Uses CPCB official categories. Not medical advice — includes disclaimer.

4. **Backtest limited by data:** Evaluated on latest chronological holdout period. More historical years would further strengthen validation.

5. **OSM facility counts:** Not implemented due to time. Using `env_type` proxy instead.

6. **Impact framing:** Showing exposure concentration, NOT health outcomes. We don't have morbidity data.

---

**Last Updated:** October 23, 2026
**Build Version:** Hackathon Submission v1.0
