# CityPulse: Mumbai — Assumptions & Design Decisions

**Documentation of assumptions made during hackathon implementation**  
**Last Updated:** October 23, 2026

---

## 1. Data & Temporal Assumptions

### 1.1 Historical Replay Mode
**Assumption:** App operates in "historical replay" mode using most recent date in predictions dataset.

**Rationale:**
- Live CPCB API integration requires authentication and rate limits
- Historical data is sufficient for prototype validation
- Allows reproducible demos without network dependency

**Implications:**
- All forecasts are retrospective (not live)
- Decision date shown as "Data as of: {date}" everywhere
- Warning banner: "Historical replay: observations through {date}"

**Future Work:** Integrate live CPCB API with auto-refresh every 6 hours.

---

### 1.2 Data Quality Thresholds
**Assumption:** 18-hour rule for valid station-days (≥18 hourly readings required).

**Rationale:**
- CPCB uses 16-hour rule; we're more conservative
- Gaps filled with linear interpolation (max 3-hour gap)
- Sensor-stuck detection: consecutive identical readings > 6 hours

**Implications:**
- 22,608 valid station-days out of raw data
- Some station-days excluded from analysis
- Coverage varies by season and station

**Alternative Considered:** 16-hour rule (CPCB standard), rejected as too permissive.

---

### 1.3 Chronological Holdout
**Assumption:** 2021-2022 train, 2023 test. Zero shuffling, zero target leakage.

**Rationale:**
- Air quality is time-series data (temporal autocorrelation)
- Random splits leak future information into training
- Chronological split simulates real deployment

**Implications:**
- Model trained on 24 months, tested on 12 months
- Forecast evaluation is forward-looking only
- Backtest uses only past data to rank zones

---

## 2. Decision Engine Assumptions

### 2.1 Weight Normalization
**Assumption:** If weights don't sum to 1.0, auto-normalize before computing priority score.

**Rationale:**
- Users may adjust weights without perfect calibration
- Normalization ensures scores remain 0-100
- Mathematical requirement: weighted sum needs normalized weights

**Implications:**
- Sidebar shows "Total = {sum}" with warning if ≠ 1.0
- Score computation divides by sum(weights)
- No error thrown for unbalanced weights

**Example:**
```python
weights = {"w_exp": 0.40, "w_pers": 0.30}  # sum = 0.70
# Normalized: {"w_exp": 0.571, "w_pers": 0.429}
```

---

### 2.2 Capacity Constraint
**Assumption:** Municipal resources limited to N teams per week (default: 5).

**Rationale:**
- Real BMC/MPCB enforcement squads are finite
- Common deployment: 5-10 teams for Greater Mumbai
- "Top-N" framing matches operational reality

**Implications:**
- Sidebar slider: 1-15 teams (default: 5)
- Leaderboard marks top-N as "INSPECT", rest as "ROUTINE"
- Backtest simulates N inspections per week

**Calibration:** Based on informal discussions with municipal officer analogs.

---

### 2.3 High-AQI Threshold
**Assumption:** AQI > 150 defines "high" (Moderate/Poor boundary).

**Rationale:**
- CPCB Moderate category starts at 101 AQI
- Poor category (151-200) triggers health advisories
- 150 is practical operational threshold

**Implications:**
- Persistence score counts days > 150
- Backtest measures: "Did top-N zones have AQI > 150?"
- Citizen guidance shifts at 150 (more cautious language)

**Alternative Considered:** 100 (Moderate start), rejected as too sensitive; 200 (Very Poor), rejected as too late.

---

### 2.4 Forecast Horizon
**Assumption:** 24-hour (next-day) forecast only. No multi-day sequences.

**Rationale:**
- Air quality is highly autoregressive (yesterday predicts today well)
- Forecast skill degrades rapidly beyond 24 hours
- Next-day is operationally actionable (deploy teams tomorrow)

**Implications:**
- Model predicts `target_next_day_aqi`
- Classifier predicts `P(AQI > 200 tomorrow)`
- No 7-day or 14-day forecasts shown

**Future Work:** Multi-step forecasting with uncertainty quantification.

---

## 3. Routing Assumptions

### 3.1 Haversine Distance
**Assumption:** Straight-line (great-circle) distance, not road routing.

**Rationale:**
- Road routing APIs (Google Maps, Mapbox) require paid keys
- Haversine sufficient for resource planning heuristic
- Disclaimer shown: "Straight-line distance, NOT actual road travel"

**Formula:**
```python
R = 6371 km  # Earth radius
a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
c = 2 * atan2(√a, √(1-a))
distance = R * c
```

**Implications:**
- Total route distance underestimates actual travel
- No traffic, road topology, or Mumbai geography considered
- User warned in UI: "Real travel will be longer"

**Alternative Considered:** OpenStreetMap OSRM (free), rejected due to setup complexity.

---

### 3.2 Nearest-Neighbor Heuristic
**Assumption:** Greedy nearest-neighbor TSP for route construction.

**Rationale:**
- Optimal TSP is NP-hard; for N=5-10, greedy is fast enough
- Municipal use case: "good enough" routing, not optimal
- Runtime: O(N²) vs exponential for exact TSP

**Implications:**
- Route may not be globally optimal
- Starting point matters (affects final distance)
- User can choose starting point (depot / highest priority)

**Quality:** Typically within 25% of optimal for small N.

---

## 4. Validation Assumptions

### 4.1 Backtest Window
**Assumption:** 7-day lookback, 7-day lookahead for weekly inspection simulation.

**Rationale:**
- Municipal inspection cycles are ~1 week
- 7-day lookback matches priority score's 7-day features
- 7-day lookahead: "Did high AQI occur in next week?"

**Methodology:**
```python
for decision_date in weekly_dates:
    # Use data from [decision_date - 7d, decision_date]
    priority = compute_rankings(recent_data)
    top_n = priority.head(N)
    
    # Check outcomes in [decision_date + 1d, decision_date + 7d]
    hit_rate = count_high_aqi_days(top_n, future_window) / total_days
```

**Implications:**
- Backtest uses ~40 weeks of 2023 data
- Each week is independent (no overlap)
- Results: +33% lift over random selection

---

### 4.2 Baseline Comparison
**Assumption:** Random selection is the baseline for backtest.

**Rationale:**
- Current practice: no systematic prioritization (ad-hoc / reactive)
- Random approximates "inspect zones arbitrarily"
- Alternative baselines (always-highest-AQI) too naive

**Implications:**
- Lift calculated as: `(strategy_hit_rate / random_hit_rate - 1) * 100`
- Random baseline is conservative (not comparing to "do nothing")
- Shows value of evidence-based prioritization

---

### 4.3 Interval Coverage
**Assumption:** Nominal 80% intervals computed via quantile regression (p10, p90).

**Rationale:**
- GradientBoostingRegressor with `loss='quantile'` trained twice (α=0.10, α=0.90)
- Nominal = stated confidence level (80%)
- Actual coverage measured on holdout

**Result:** 74.1% empirical coverage → undercovering by 5.9pp.

**Implications:**
- Intervals are NOT calibrated 80% guarantees
- Shown honestly in validation tab
- Users warned: "Uncertainty range, not guaranteed bounds"

---

## 5. Citizen View Assumptions

### 5.1 CPCB Health Guidance
**Assumption:** Health guidance text is verbatim from CPCB official categories.

**Source:** CPCB National Air Quality Index guidelines (2014, revised 2021).

**Categories:**
- Good (0-50): "Air quality is satisfactory..."
- Satisfactory (51-100): "May be risk for unusually sensitive people..."
- Moderate (101-200): "Sensitive groups may experience health effects..."
- Poor (201-300): "Health alert: everyone may experience effects..."
- Very Poor (301-400): "Health warning of emergency conditions..."
- Severe (401-500): "Everyone should avoid all outdoor activity..."

**Implications:**
- No custom health advice (liability reasons)
- Disclaimer: "Not medical advice; consult healthcare provider"
- Cautious language ("consider limiting" not "do not")

---

### 5.2 Sensitive Groups
**Assumption:** Sensitive = children, elderly, respiratory conditions, heart disease.

**Rationale:**
- CPCB and WHO definitions align
- Medically accepted vulnerability categories
- Common sense for Indian urban context

**Implications:**
- Separate guidance shown for sensitive groups
- Health protection tips vary by AQI level
- No individual medical assessment provided

---

## 6. Technical Assumptions

### 6.1 Caching Strategy
**Assumption:** Heavy operations cached via `@st.cache_data` with 1-hour TTL.

**Operations Cached:**
- Priority score computation
- Monte Carlo simulations (500 runs)
- Route planning
- Backtest metrics

**Rationale:**
- Streamlit reruns on every interaction
- Expensive operations (Monte Carlo) must be cached
- 1-hour TTL balances freshness vs performance

**Implications:**
- First load of Tab 2 slow (~15s), subsequent instant
- Changing weights invalidates cache (recomputes)
- Memory usage: ~50MB for cached simulations

---

### 6.2 Random Seed
**Assumption:** NumPy random seed = 42 for reproducibility.

**Rationale:**
- Monte Carlo simulations must be reproducible for demos
- Seed ensures same perturbations every run
- Industry standard: 42 (hitchhiker's guide reference)

**Implications:**
- Rank stability results identical across runs
- Demo is deterministic (good for presentations)
- Production would use random seed for robustness

---

### 6.3 No API Keys Required
**Assumption:** Zero paid APIs, zero authentication, 100% local computation.

**Rationale:**
- Hackathon constraint: judges must clone and run without setup
- Free APIs (CPCB, Open-Meteo) don't require keys
- Reproducibility requirement

**Implications:**
- Historical data bundled in repo
- No live updates (see assumption 1.1)
- No road routing (see assumption 3.1)
- No satellite data (future work)

---

## 7. UI/UX Assumptions

### 7.1 Dark Theme Default
**Assumption:** Dark mode is default and only theme.

**Rationale:**
- Municipal officers often work in low-light environments (field, vehicles)
- Dark themes reduce eye strain for data-heavy dashboards
- Modern aesthetic for tech-forward presentation

**Implications:**
- No light mode toggle
- WCAG AA contrast ratios maintained
- Color palette optimized for dark backgrounds

---

### 7.2 Material Symbols Icons
**Assumption:** Streamlit native `:material/icon_name:` syntax, zero emojis.

**Rationale:**
- Professional appearance (government/municipal context)
- Consistent icon style across tabs
- No external CDN dependencies

**Implications:**
- No fallback for old Streamlit versions
- Icons are semantic, not decorative
- Zero emoji usage (🏙️ in branding only)

---

## 8. Limitations We Accept

### 8.1 Model Doesn't Beat Persistence
**Accepted Limitation:** MAE 20.3 (model) vs 19.4 (persistence).

**Why Not Fixed:**
- Air quality is heavily autoregressive
- Beating yesterday requires satellite AOD, hyper-local sensors
- Shown honestly in validation tab

**Value Proposition:** Priority scoring beats random (not persistence forecast).

---

### 8.2 Intervals Undercover
**Accepted Limitation:** 74.1% actual vs 80% nominal coverage.

**Why Not Fixed:**
- Quantile regression not perfectly calibrated on this dataset
- Conformal prediction would fix, but complexity overhead high
- Shown honestly with disclaimer

**Mitigation:** Label as "uncertainty range" not "80% guarantee".

---

### 8.3 Straight-Line Routing
**Accepted Limitation:** Haversine distance, not road network.

**Why Not Fixed:**
- Road routing APIs require payment (Google Maps, Mapbox)
- Free alternatives (OSRM) need setup, increase complexity
- Shown honestly with disclaimer

**Mitigation:** "Route is heuristic; real travel will be longer."

---

## 9. Assumptions for Future Work

### 9.1 Live API Integration
**Assumption:** CPCB will maintain stable API with reasonable rate limits.

**Plan:** Poll every 6 hours, cache responses, fall back to historical if unavailable.

---

### 9.2 Satellite Data
**Assumption:** INSAT-3D AOD data will be available (free or affordable license).

**Plan:** Integrate 1km resolution optical depth to beat persistence baseline.

---

### 9.3 Multi-City Deployment
**Assumption:** CPCB station lists and data formats are consistent across cities.

**Plan:** Parametrize by city, reuse pipeline with config overrides.

---

## 10. Assumptions We Rejected

### 10.1 ❌ Synthetic Data
**Rejected:** Generating fake AQI readings to fill gaps.

**Reason:** Violates "honest data" principle. All numbers must be real.

---

### 10.2 ❌ LLM-Generated Recommendations
**Rejected:** Using GPT/Claude to generate action recommendations.

**Reason:** Not reproducible, not explainable, requires API key. Rule-based is transparent.

---

### 10.3 ❌ Health Outcome Claims
**Rejected:** Estimating "lives saved" or "hospitalizations prevented".

**Reason:** We don't have morbidity data. Impact framing stays on exposure concentration.

---

### 10.4 ❌ Perfect Calibration
**Rejected:** Spending time on conformal prediction for perfect 80% intervals.

**Reason:** Diminishing returns for prototype. Honesty + disclaimer is sufficient.

---

## 11. How to Validate Assumptions

### If You're a Judge:
1. **Data Quality:** Check `data/processed/mumbai_aqi_daily_clean.parquet` row counts
2. **Weight Normalization:** Adjust sidebar weights to 0.50, 0.30 → see "Total = 0.80" warning
3. **Backtest:** Tab 8 shows +33% lift → verify it's computed from real data
4. **Route Distance:** Tab 3 → note "straight-line distance" disclaimer
5. **Interval Coverage:** Tab 8 → see 74.1% vs 80%, with honest statement

### If You're a User:
1. **Historical Replay:** Look for "Data as of: {date}" chip everywhere
2. **Honest Validation:** Tab 8 → check "Where We're Honest" column
3. **Disclaimers:** Route tab, citizen view, briefing → all have limitation statements

---

## 12. Summary of Key Assumptions

| Domain | Assumption | Impact | Rationale |
|--------|-----------|--------|-----------|
| **Data** | Historical replay mode | No live updates | API complexity |
| **Data** | 18-hour validity rule | 22K valid days | Conservative QC |
| **Weights** | Auto-normalize if ≠ 1.0 | Forgiving UX | User convenience |
| **Capacity** | N=5 teams default | Top-5 marked | Municipal reality |
| **Threshold** | AQI > 150 = "high" | Backtest metric | Operational standard |
| **Routing** | Haversine distance | Underestimates travel | No paid APIs |
| **Routing** | Nearest-neighbor TSP | ~25% suboptimal | Fast enough for N<10 |
| **Backtest** | 7-day windows | 40 weeks tested | Weekly cycles |
| **Baseline** | Random selection | Conservative lift | Current practice |
| **Intervals** | Quantile regression | 74% coverage | Not conformal |
| **Health** | CPCB guidance text | No custom advice | Liability |
| **Caching** | 1-hour TTL | Fresh enough | Performance |
| **Seed** | NumPy seed=42 | Reproducible | Demo reliability |

---

**Assumptions Document Version:** 1.0  
**Last Reviewed:** October 23, 2026  
**Reviewers:** Ratnesh, Rishi, Shreya  
**Status:** FINAL FOR HACKATHON
