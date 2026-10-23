# CityPulse: Mumbai

Air quality decision-support prototype for the Mumbai Metropolitan Region. CityPulse ranks monitoring zones by priority using public CPCB air quality and Open-Meteo weather data, and provides explainable, rule-based action dossiers showing why each zone ranked where it did.

[Live demo](https://citypulse-mumbai.streamlit.app) | [Evaluation report](reports/EVALUATION.md) | [CV evaluation report](reports/phase1b_cv.md) | [Deployment guide](DEPLOYMENT.md) | [Data sources](DATA_SOURCES.md)

> **Status: prototype.** CityPulse supports municipal planning and prioritisation. It is not an official warning system and does not replace statutory monitoring by the CPCB or MPCB.

## Overview

**Intended user:** a municipal environment or public health officer (BMC / MPCB) allocating limited inspection, road sweeping, and dust-suppression resources.

**Decision supported:** which zones should be prioritised this week, given an inspection capacity of N zones?

**Data:** 597,912 deduplicated hourly AQI records from 36 station labels and 26,280 hourly weather observations, covering the latest multi-year baseline dataset.

---

## Complete Feature Suite

CityPulse delivers a comprehensive 12-module operational console designed for rapid administrative triage:

### 1. Decision & Operational Triage
- **Priority Ranking & Triage (Tab 1):** Five-component composite score (exposure, persistence, trend, forecast, vulnerability) with dynamic top-N capacity flags and geospatial ward mapping.
- **Action Dossiers (Tab 1):** Context-aware, rule-based municipal interventions (e.g., mechanical sweeping, wet-suppression, anti-smog guns) mapped to local environment types with explicit operational caveats.
- **Why-This-Station Waterfall Explainer (Tab 1):** Stacked contribution charts showing point-by-point score decomposition across all five criteria for full decision auditability.
- **What-If Policy Simulator (Tab 2):** Real-time interactive weight re-balancing with a **500-run Monte Carlo rank stability analysis** and perturbation heatmaps to test policy sensitivity.
- **Inspection Route Planner (Tab 3):** Haversine-based nearest-neighbour TSP tour optimizer generating stop-by-stop schedules, leg distances, and cumulative travel budgets for field crews.
- **Printable Briefing Export (Tab 4):** One-click executive summary generator exporting clean, print-optimised HTML reports (and optional PDF) for weekly administrative briefings.

### 2. Empirical Insights & Environmental Diagnostics
- **Historical Patterns (Tab 5):** Empirical analyses of diurnal traffic peaks, spatial station heterogeneity, and the dramatic monsoon washout vs winter inversion cycle.
- **Meteorological Coupling (Tab 6):** ERA5 surface reanalysis diagnostics exploring wind speed/direction correlations, sea-breeze ventilation fronts, and atmospheric stagnation risks.
- **Case Studies & Extreme Episodes (Tab 9):** Deep-dive empirical reviews of multi-day Diwali episode elevations, winter trapping episodes, and coastal vs inland transport gradients.

### 3. Model Evaluation, Validation & Trust
- **Forecast Performance (Tab 7):** Comprehensive point and probabilistic evaluation against persistent baselines, including parity plots, calibration curves, and PR-AUC/ROC-AUC curves.
- **Honest Validation & Backtest (Tab 8):** Simulation of weekly inspection cycles demonstrating double-digit lift over random allocation, paired with empirical coverage tracking for 80% prediction intervals.
- **Audit & Governance (Tab 12):** Public data provenance cards, licensing audits (CPCB NDSAP, Open-Meteo CC BY 4.0, OSM ODbL), and transparent disclosures of model limitations.

### 4. Citizen Engagement & Pitch Walkthrough
- **Citizen View (Tab 10):** Public-friendly view with official CPCB health guidance, sensitive group advisories, 7-day outlooks, and downloadable shareable social cards.
- **Guided Demo Walkthrough (Tab 11):** 8-step interactive presentation pitch mode with metric counters and auto-advance capability designed for hackathon judges and stakeholders.

---

## Key Empirical Findings

- **Seasonal Dynamics:** Mean station-day AQI drops to 63.9 during the monsoon washout (June–September) and climbs to 185.0 during winter inversions (December–February).
- **Spatial Heterogeneity:** Among stations with at least 150 valid days, Mazgaon averages 153.0 AQI while Borivali East averages 88.6 AQI.
- **Wind Coupling:** Wind speed and daily AQI correlate at $r = -0.25$. AQI above 200 occurs on 16.2% of station-days in the lowest wind quintile versus 5.8% in the highest.

Full analysis: [`reports/eda_findings.md`](reports/eda_findings.md).

---

## Machine Learning & Model Validation

CityPulse uses an expanding date-based evaluation strategy to prevent target leakage and simulate real-world municipal deployment:

1. **Phase 1b Cross-Validation:** Three expanding date-based training folds with inner-split Ridge tuning and 10 candidate architectures. The winning candidate is **LightGBM L1 on Persistence Residuals** (`LightGBM_L1_Residual`), evaluated with paired date-block bootstrap 95% confidence intervals (2,000 resamples). Full results in [`reports/phase1b_cv.md`](reports/phase1b_cv.md).
2. **Holdout Benchmark:** Evaluated on the chronological holdout window:

**Next-Day Mean AQI Benchmark**

| Model                       |       MAE |      RMSE |       R^2 | Skill vs Persistence |
| :-------------------------- | --------: | --------: | --------: | -------------------: |
| Persistence (t-1)           | **19.42** |     30.38 |     0.820 |                 0.0% |
| Seasonal naive (t-7)        |     34.57 |     50.01 |     0.513 |               -78.0% |
| Ridge regression            |     19.58 | **28.65** | **0.840** |                -0.8% |
| Histogram gradient boosting |     20.35 |     29.92 |     0.826 |                -4.8% |

**Severe Episode Risk Classification (AQI > 200)**

| Model             | Precision |    Recall |        F1 |    PR-AUC |   ROC-AUC |     Brier |
| :---------------- | --------: | --------: | --------: | --------: | --------: | --------: |
| State persistence | **0.716** |     0.717 | **0.717** |       N/A |       N/A |       N/A |
| Gradient boosting |     0.593 | **0.872** |     0.706 | **0.811** | **0.955** | **0.076** |

**Honest Takeaway:** Daily ambient AQI is strongly autoregressive. While point models remain competitive with persistence, the machine learning models provide significant value in **probabilistic risk screening (PR-AUC 0.811, Recall 0.872)** and in driving the multi-criteria prioritization policy.

---

## Priority Score Formulation

The score (0–100) is a transparent, explainable weighted average across five normalised operational criteria:

$$\text{Priority Score} = \frac{w_{\text{exp}} S_{\text{exp}} + w_{\text{pers}} S_{\text{pers}} + w_{\text{trend}} S_{\text{trend}} + w_{\text{fore}} S_{\text{fore}} + w_{\text{gap}} S_{\text{gap}}}{\sum w}$$

- **$S_{\text{exp}}$ (Exposure):** Recent 7-day cumulative mean AQI relative to national ambient standards.
- **$S_{\text{pers}}$ (Persistence):** Frequency of Moderate/Poor threshold exceedances (AQI > 150) in the past week.
- **$S_{\text{trend}}$ (Acceleration):** 7-day rate of worsening (today vs rolling baseline).
- **$S_{\text{fore}}$ (Forecast Risk):** Calibrated next-day probability of an AQI > 200 event.
- **$S_{\text{gap}}$ (Vulnerability / Gap):** Transit corridor siting, micro-environment vulnerability, and regional monitoring sparsity.

---

## Getting Started

Requires Python 3.10 or newer. No external API keys or subscriptions are required.

```bash
# Clone the repository
git clone https://github.com/RishiBuilds/CityPulse.git
cd CityPulse

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run full test suite (36 unit & integration tests)
python -m pytest

# Launch the Streamlit dashboard
streamlit run app.py
```

The application runs locally at `http://localhost:8501`. Detailed hosting and container instructions for Streamlit Community Cloud and Hugging Face Spaces are provided in [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Known Limitations

- **Autoregressive Baseline:** Ambient AQI is heavily driven by previous-day state. Beating persistence on pure MAE citywide would require live satellite AOD plumes, hyper-local sensor meshes (< 500m), real-time traffic telemetry, and active construction registers.
- **Spatial Coverage:** Regulatory CAAQMS stations cluster near Western and Central Express highways; unmonitored wards require spatial proxy interpolation.
- **Point Telemetry:** Station readings represent localized air basins and do not imply whole-ward homogeneity.
- **Health Proxy:** Impact analyses reflect exposure concentration proxies, not clinical morbidity registries.

## Responsible Use

CityPulse is an operational screening and resource triage tool. It is intended to guide physical inspections and supportive mitigation, not to serve as automated justification for punitive enforcement.

## Data Attribution & Licences

| Data | Source | Licence |
| :--- | :--- | :--- |
| **Air Quality Telemetry** | CPCB & MPCB CAAQMS Archives | Government Open Data (NDSAP) — [DATA_SOURCES.md](DATA_SOURCES.md) |
| **Surface Meteorology** | [Open-Meteo](https://open-meteo.com) (ERA5 Reanalysis) | Creative Commons Attribution 4.0 (CC BY 4.0) |
| **Spatial Infrastructure** | [OpenStreetMap](https://www.openstreetmap.org) | Open Database License (ODbL) |

## Authors & Licence

Built by **Ratnesh, Rishi, and Shreya** for **HackAMatch 1.0**. Released under the [MIT License](LICENSE).
