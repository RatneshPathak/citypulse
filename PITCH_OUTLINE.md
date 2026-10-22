# CityPulse: Mumbai — 5-Slide Pitch Deck Outline

**For: HackAMatch 1.0 Final Judging**  
**Timing: 5 minutes (1 min per slide)**

---

## Slide 1: Problem & User

### Title
**Mumbai's Air Quality Decision Bottleneck**

### Visual
- Map of Mumbai with 36 monitoring stations (dots)
- 5 inspection team icons trying to cover 36 zones
- Red zones glowing (high AQI)

### Key Points
- **36 monitoring stations** across Mumbai Metropolitan Region
- **600K+ hourly AQI records** (2021-2023)
- **Finite municipal resources:** 5-10 inspection teams per week
- **Decision challenge:** *"Which zones need attention THIS WEEK?"*

### The User
**Municipal environmental officer (BMC / MPCB role)**
- Deploys anti-smog mist cannons, dust inspections, traffic anti-idling
- Must prioritize: cannot inspect all zones
- Needs defensible, evidence-based recommendations

### The Ask
> "How do we translate 600K data points into a **ranked action queue** that's transparent, validated, and actionable?"

---

## Slide 2: Solution Architecture

### Title
**CityPulse: Multi-Criteria Decision Engine**

### Visual
```
┌─────────────────────────────────────────────────────┐
│  CPCB AQI Data  +  Open-Meteo Weather  +  OSM Land │
│  (597K records)     (26K observations)   (Context)  │
└───────────────────┬─────────────────────────────────┘
                    ▼
        ┌───────────────────────┐
        │  DATA QUALITY & QC    │
        │  18-hour rule         │
        │  Sensor-stuck filter  │
        └───────┬───────────────┘
                ▼
        ┌───────────────────────┐
        │  FEATURE ENGINEERING  │
        │  7-day rolling stats  │
        │  Weather lag features │
        └───────┬───────────────┘
                ▼
        ┌───────────────────────┐
        │  FORECAST MODELS      │
        │  Gradient Boosting    │
        │  80% Intervals        │
        └───────┬───────────────┘
                ▼
┌───────────────────────────────────────────────┐
│  PRIORITY SCORE (0-100)                       │
│  • Exposure (7-day mean AQI)           30%    │
│  • Persistence (days > 150)            25%    │
│  • Trend Acceleration                  15%    │
│  • Forecast Risk (P(AQI > 200))        20%    │
│  • Vulnerability Context               10%    │
└───────────────────┬───────────────────────────┘
                    ▼
        ┌───────────────────────┐
        │  RANKED ACTION QUEUE  │
        │  Top-N for inspection │
        └───────────────────────┘
```

### Key Points
- **100% free, open data** (CPCB, Open-Meteo, OSM)
- **5-component score**: Exposure + Persistence + Trend + Forecast + Vulnerability
- **Transparent weights**: adjustable by policy (What-If Simulator)
- **Outputs**: Ranked list, route plan, printable briefing

---

## Slide 3: Evidence & Validation

### Title
**Does It Actually Work? Honest Validation**

### Visual
- Split-screen comparison:
  - **Left:** Priority Strategy (green bar: 42.3% hit rate)
  - **Right:** Random Selection (gray bar: 31.8% hit rate)
- Arrow showing **+33% lift**

### Validation Metrics Table

| Metric | Value | Context |
|--------|-------|---------|
| **Backtest Hit Rate** | 42.3% | Top-5 zones had AQI > 150 this % of time |
| **Random Baseline** | 31.8% | Random selection performance |
| **Lift vs Random** | **+33%** | ✅ Measurable efficiency gain |
| **Model MAE** | 20.3 | ⚠️ Doesn't beat persistence (19.4) |
| **80% Interval Coverage** | 74.1% | ⚠️ Undercovers — not calibrated |
| **Backtest Period** | 2023 | Chronological holdout (no leakage) |

### Key Points
- **Rigorous backtest**: 2023 holdout, weekly simulations
- **Priority strategy beats random by 33%** — concentrates resources efficiently
- **Honest about limitations**: Model doesn't beat persistence; intervals undercover
- **Rank stability tested**: Monte Carlo with 500 weight perturbations

### Honesty Wins Trust
> "We show judges **where it works AND where it doesn't**. That's how you build trust."

---

## Slide 4: Impact & Stakeholder Value

### Title
**Measurable Impact (Computed from Data)**

### Visual
- Donut chart: "Top-5 zones account for **58%** of all high-AQI station-days in 2023"
- Icon grid showing:
  - 🏛️ **Municipal Officers**: Defensible prioritization, printable briefings
  - 🏘️ **Citizens**: Simplified health guidance, shareable AQI cards
  - 🎓 **Researchers**: Open-source code, reproducible pipeline

### Impact Metrics (Real, Not Projected)

| Stakeholder | Computed Benefit |
|-------------|------------------|
| **Municipal (BMC/MPCB)** | Top-5 zones capture 58% of high-AQI station-days → resource concentration |
| **Field Inspectors** | One-click briefing export (HTML/PDF) with evidence & actions |
| **Policy Makers** | What-If Simulator shows rank sensitivity to weight changes |
| **Citizens** | Simplified health guidance (CPCB categories), no medical claims |
| **Technical Community** | MIT-licensed, 100% reproducible, zero paid APIs |

### Key Points
- **NOT claiming health outcomes** (we don't have morbidity data)
- **Showing exposure concentration**: Top-5 zones are where high AQI happens
- **Practical artifacts**: Briefing PDFs, route maps, AQI cards

### What We're NOT Saying
❌ "This will save X lives" (no health data)  
❌ "This is THE pollution source" (no source attribution)  
✅ "This helps prioritize WHERE to look, based on evidence"

---

## Slide 5: Next Steps & Roadmap

### Title
**From Prototype to Production**

### Visual
- Timeline with 4 phases:
  - ✅ **Phase 1 (Now)**: Historical replay prototype
  - 🔄 **Phase 2 (Next 3 months)**: Live CPCB API integration
  - 🚀 **Phase 3 (6 months)**: Satellite AOD data, beat persistence
  - 🌍 **Phase 4 (12 months)**: Multi-city deployment

### Immediate Next Steps (3 months)

| Action | Why | Impact |
|--------|-----|--------|
| **Live CPCB API** | Real-time data instead of historical replay | Operational readiness |
| **SMS/WhatsApp Alerts** | Push notifications to citizens | Direct public health reach |
| **Satellite AOD Integration** | High-frequency dust/smoke plumes | Beat persistence baseline |
| **Municipal Pilot** | 8-week trial with BMC Ward X | Real-world validation |

### Multi-City Expansion (12 months)

- **Delhi**: 37 stations, winter smog crisis
- **Pune**: 15 stations, industrial corridors
- **Kolkata**: 12 stations, seasonal burning
- **Bengaluru**: 25 stations, traffic hot spots

### Technical Roadmap

| Milestone | Description | Status |
|-----------|-------------|--------|
| ✅ **Prototype** | Historical replay, 11 tabs, validation backtest | COMPLETE |
| 🔄 **API Integration** | Live CPCB feed, auto-refresh | IN PROGRESS |
| 🚀 **AOD Data** | INSAT-3D geostationary optical depth | PLANNED |
| 🌍 **Multi-City** | Reusable pipeline for 10+ cities | ROADMAP |

### Funding Ask (If Applicable)

**Bootstrapped so far:** Zero cloud costs (free tier), zero APIs  
**Scaling needs:** 
- **₹50K**: Live API infrastructure (Cloud Run, cron jobs)
- **₹1.5L**: Satellite data licenses (if not free)
- **₹2L**: 6-month pilot with municipal partner

### Open-Source Philosophy
> "CityPulse will always be **MIT-licensed**. The public good comes first."

---

## 🎯 Closing Statement (30 seconds)

> "Mumbai has 36 air quality zones and 5 inspection teams. **That's a prioritization problem.**
> 
> CityPulse solves it with:
> - ✅ **Multi-criteria evidence scoring**
> - ✅ **Rigorous validation** (33% lift over random)
> - ✅ **Practical outputs** (route plans, briefings, citizen cards)
> - ✅ **100% open data** (CPCB, Open-Meteo, OSM)
> - ✅ **Honest limitations** (where it doesn't work)
> 
> We're not claiming to predict health outcomes. We're helping officers **decide where to look**, based on evidence.
> 
> **Next step:** 8-week pilot with BMC. Let's turn this prototype into policy.
> 
> **CityPulse: Predict. Explain. Act.** Thank you."

---

## 📊 Appendix: Supporting Data

### Key Statistics to Memorize

- **597,912** hourly AQI records (2021-2023)
- **26,280** hourly weather observations
- **36** monitoring stations
- **22,608** valid station-days (after 18-hour rule)
- **33%** lift over random selection
- **58%** of high-AQI days in top-5 zones
- **500** Monte Carlo runs for rank stability
- **74.1%** empirical interval coverage (vs 80% nominal)
- **19.4 vs 20.3** MAE (persistence vs model)

### Anticipated Judge Questions

**Q: Why doesn't the model beat persistence?**  
A: Daily air quality is heavily autoregressive. To beat yesterday, you need satellite AOD, hyper-local sensors, and live traffic data. We show this honestly in our validation.

**Q: How do you ensure equity across zones?**  
A: The vulnerability component includes highway corridors and industrial proximity. Future work: OSM facility counts (hospitals, schools) as population-sensitivity proxy.

**Q: What if the policy changes?**  
A: Tab 2: What-If Simulator. Adjust weights in sidebar, see rankings update. Monte Carlo stability shows which zones are robust.

**Q: Can citizens use this?**  
A: Yes. Tab 9: Citizen Mode. Simplified health guidance (CPCB categories), shareable AQI cards. No medical claims.

**Q: Is this open-source?**  
A: MIT License. Every line of code, every dataset source, every evaluation metric. Zero paid APIs.

---

**Pitch Deck File:** `reports/slides/CityPulse_Final_Pitch.pptx`  
**Last Updated:** October 23, 2026  
**Rehearsal Status:** READY
