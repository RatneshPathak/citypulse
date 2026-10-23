# CityPulse: Mumbai

Air quality decision-support prototype for the Mumbai Metropolitan Region. CityPulse ranks monitoring zones by priority using public CPCB air quality and Open-Meteo weather data, and shows why each zone ranked where it did.

[Live demo](https://citypulse-mumbai.streamlit.app) | [Evaluation report](reports/EVALUATION.md) | [Deployment guide](DEPLOYMENT.md) | [Data sources](DATA_SOURCES.md)

> **Status: prototype.** CityPulse supports planning and prioritisation. It is not an official warning system and does not replace monitoring by the CPCB or MPCB.

## Overview

**Intended user:** a municipal environment or public health officer allocating limited inspection and mitigation resources.

**Decision supported:** which zones should be prioritised this week, given a capacity of N zones?

**Data:** 597,912 deduplicated hourly AQI records from 36 station labels and 26,280 hourly weather observations, covering 2021-2023.

## Features

- **Priority ranking:** five-component score (exposure, persistence, trend, forecast, vulnerability) with a top-N action flag.
- **What-if simulator:** adjust criterion weights and test rank stability with a 500-run Monte Carlo analysis.
- **Route planner:** nearest-neighbour inspection tour using haversine distance.
- **Briefing export:** printable weekly report in HTML and PDF.
- **Score breakdown:** waterfall charts explaining each zone's rank.
- **Validation backtest:** chronological 2023 holdout with lift versus random selection and interval coverage.
- **Citizen mode:** plain-language health guidance by CPCB AQI category.

## Key findings

- Mean station-day AQI is 63.9 in June-September and 185.0 in December-February.
- Among stations with at least 150 valid days, Mazgaon averages 153.0 AQI and Borivali East 88.6.
- Wind speed and AQI correlate at r = -0.25. AQI above 200 occurs on 16.2% of station-days in the lowest wind quintile versus 5.8% in the highest. Season and location may confound this.

Calculations: [`reports/eda_findings.md`](reports/eda_findings.md).

## Validation

Models are trained on 2021-2022 and tested forward on 2023, with no shuffling or target leakage.

**Next-day mean AQI**

| Model                       |       MAE |      RMSE |       R^2 | Skill vs persistence |
| :-------------------------- | --------: | --------: | --------: | -------------------: |
| Persistence (t-1)           | **19.42** |     30.38 |     0.820 |                 0.0% |
| Seasonal naive (t-7)        |     34.57 |     50.01 |     0.513 |               -78.0% |
| Ridge regression            |     19.46 | **28.62** | **0.841** |                -0.2% |
| Histogram gradient boosting |     20.33 |     29.97 |     0.825 |                -4.7% |

**AQI > 200 event classification**

| Model             | Precision |    Recall |        F1 |    PR-AUC |   ROC-AUC |     Brier |
| :---------------- | --------: | --------: | --------: | --------: | --------: | --------: |
| State persistence | **0.716** |     0.717 | **0.717** |       N/A |       N/A |       N/A |
| Gradient boosting |     0.592 | **0.877** |     0.707 | **0.811** | **0.954** | **0.077** |

Neither trained point model beats persistence on citywide MAE, so the dashboard is a historical decision replay rather than a live forecast. Nominal 80% prediction intervals reach 74.1% empirical coverage and should not be treated as calibrated.

## Priority score

The score (0-100) is a weighted average of five normalised criteria:

```
score = (w_exp*S_exp + w_pers*S_pers + w_trend*S_trend + w_fore*S_fore + w_gap*S_gap) / sum(w)
```

The user sets capacity N, and the top N zones are flagged as actionable. The score is a decision heuristic, not a health forecast.

## Getting started

Requires Python 3.10 or newer. No API keys are needed.

```bash
git clone https://github.com/RishiBuilds/CityPulse.git
cd CityPulse
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover tests
streamlit run app.py
```

The app runs at `http://localhost:8501`. Deployment steps for Streamlit Community Cloud and Hugging Face Spaces are in [DEPLOYMENT.md](DEPLOYMENT.md).

## Limitations

- Daily AQI is strongly autoregressive, and weather data alone does not resolve local emission changes. Beating persistence would likely need satellite AOD, dense local sensors, live traffic data and construction permit records.
- Monitoring stations cluster along highway corridors in western and central Mumbai, so coverage is uneven.
- Station readings are point measurements and do not represent whole wards.
- No health outcome data is used.

## Responsible use

CityPulse is for screening and triage. It should not be the sole basis for punitive enforcement without physical inspection.

## Data attribution

| Data            | Source                               | Licence                                |
| :-------------- | :----------------------------------- | :------------------------------------- |
| Air quality     | CPCB and MPCB                        | See [DATA_SOURCES.md](DATA_SOURCES.md) |
| Weather         | [Open-Meteo](https://open-meteo.com) | CC BY 4.0                              |
| Spatial context | OpenStreetMap contributors           | ODbL                                   |

## Authors and licence

Ratnesh, Rishi and Shreya. Released under the [MIT License](LICENSE).
