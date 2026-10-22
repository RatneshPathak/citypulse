# CityPulse — Predict. Explain. Act.

A decision-support prototype built for **HackAMatch 1.0 (Data Mavericks × NSDC) — Data Science + AI Challenge**.

CityPulse uses free public data to help spot air-quality problems in **Mumbai**, understand the signals behind them, and decide where to focus attention.

> **Status:** prototype. This is NOT an official warning system and is not a substitute for expert judgement.

> Fill in every `<...>` placeholder with your real results before submitting. Remove this note when done.

---

## 1. Problem and intended user

- **Problem:** Which monitoring stations in Mumbai are likely to see poor air quality, and where should attention go first?
- **Intended user:** a municipal or ward-level officer who prioritises pollution-control actions and public advisories.
- **Geography and time scope:** Mumbai, `<start date>` to `<end date>`
- **Decision supported:** which stations/areas to prioritise, and when.

## 2. The core loop

| Step | What CityPulse does |
|---|---|
| **Discover** | Finds patterns in historical air-quality data (time of week, season, station differences). |
| **Predict** | Forecasts `<AQI / pollutant>` for the next `<horizon>` and compares it with a simple baseline. |
| **Explain** | Shows the evidence, forecast error range and a data-freshness label. |
| **Act** | Shows a risk tier (a heuristic, not a probability) and a suggested next step. |

## 3. Key findings

Use only results from your notebook (`CityPulse_AQI_Cleaning_EDA.ipynb`). Do not include numbers you have not computed.

1. `<finding 1 + chart>`
2. `<finding 2 + chart>`
3. `<finding 3 + chart>`

## 4. Method and validation

- **Split:** chronological (train on earlier data, test on the most recent period). No random shuffling.
- **Baseline:** `<persistence / seasonal naive>`
- **Model:** `<e.g. Random Forest / Ridge on lag features>`
- **Metrics:** MAE and RMSE for baseline vs model.
- **Results:** `<paste actual MAE/RMSE from the notebook>`
- **Uncertainty:** forecast range from test-set residuals (`<e.g. 10th–90th percentile>`).
- **Risk tier:** rule-based heuristic on forecast values using `<AQI category thresholds>`. It is not a validated probability.
- **Leakage control:** features use only information available at forecast time.

Analysis notebook: [`CityPulse_AQI_Cleaning_EDA.ipynb`](CityPulse_AQI_Cleaning_EDA.ipynb)

## 5. Data

Full details: [`DATA_STATEMENT.md`](DATA_STATEMENT.md)

| Source | URL | Access date | Licence / terms | Fields used |
|---|---|---|---|---|
| `<source 1>` | `<url>` | `<date>` | `<licence>` | `<fields>` |
| `<source 2>` | `<url>` | `<date>` | `<licence>` | `<fields>` |

All data is public and free to access. No paid APIs, paid datasets or subscriptions are required. No synthetic data is presented as real-world evidence.

## 6. Run it locally

Requires Python 3.10+.

```bash
git clone https://github.com/RatneshPathak/citypulse.git
cd citypulse

python -m venv venv
# Windows (Git Bash):
source venv/Scripts/activate
# Windows (cmd/PowerShell): venv\Scripts\activate
# macOS / Linux: source venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

- No API keys, passwords or private data are needed to run the demo.
- `<Describe where processed data lives and how to rebuild it from the notebook if the app needs it.>`

## 7. Project structure

```
citypulse/
  CityPulse_AQI_Cleaning_EDA.ipynb   # cleaning + exploratory analysis
  app.py                             # Streamlit dashboard
  src/                               # helper scripts (e.g. profile_data.py)
  notebooks/                         # additional notebooks
  data/                              # processed data used by the app
  DATA_STATEMENT.md
  requirements.txt
  README.md
```

## 8. Limitations

Keep this specific and honest. Adapt to what you found:

- Coverage gaps: `<stations/periods with missing data and how handled>`
- Station readings may not represent every neighbourhood in Mumbai.
- No ground-truth health outcomes, so the risk tier is a heuristic.
- Correlation in the analysis does not establish causation.
- Forecast skill vs baseline: `<better / similar / worse on the test period>`

## 9. Responsible use

CityPulse is an educational prototype, not an emergency-warning system. Recommendations are prompts for expert review. No personal or sensitive data is used or published.

## 10. AI assistance and third-party components

- **AI assistance:** `<describe accurately, e.g. an AI assistant was used for planning, code drafting and README drafting; the team reviewed, ran and can explain all code and results>`
- **Open-source libraries:** pandas, NumPy, scikit-learn, Streamlit, Plotly, `<others>` — used under their respective licences.
- **Data attribution:** `<source names; OpenStreetMap contributors if maps are used>`

## 11. Team

| Member | Role |
|---|---|
| Ratnesh Pathak | Lead — data, analysis, modelling |
| Rishi Chaurasiya | `<role, e.g. data sourcing, documentation>` |
| Shreya Pandey | `<role, e.g. app, charts, presentation>` |

## 12. Hackathon

HackAMatch 1.0 — Data Mavericks × NSDC. Problem statement: *CityPulse*.