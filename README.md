# CityPulse — Predict. Explain. Act.

A decision-support prototype built for **HackAMatch 1.0 (Data Mavericks × NSDC) — Data Science + AI Challenge**.

CityPulse uses free public data to help a city spot air-quality problems, understand the signals behind them, and decide where to focus attention.

> **Status:** prototype. This is NOT an official warning system and is not a substitute for expert judgement.

> Fill in every `<...>` placeholder before submitting. Remove this note when done.

---

## 1. Problem and intended user

- **Problem:** `<one sentence, e.g. which monitoring stations in <CITY> are likely to need attention for poor air quality in the next day(s)>`
- **Intended user:** `<e.g. a municipal or ward-level officer who prioritises pollution-control actions>`
- **Geography and time scope:** `<CITY>`, `<start date>` to `<end date>`
- **Decision supported:** `<e.g. which stations/areas to prioritise for advisories or inspection>`

## 2. The core loop

| Step | What CityPulse does |
|---|---|
| **Discover** | Finds patterns in historical air-quality data (time of week, season, station differences). |
| **Predict** | Forecasts `<pollutant/AQI>` for the next `<horizon>` and compares it with a simple baseline. |
| **Explain** | Shows the evidence, forecast error range, and data-freshness label. |
| **Act** | Shows a risk tier (a heuristic, not a probability) and a suggested next step. |

## 3. Key findings

Replace with your real results only. Do not include numbers you have not computed.

1. `<finding 1 + chart reference>`
2. `<finding 2 + chart reference>`
3. `<finding 3 + chart reference>`

## 4. Method and validation

- **Split:** chronological (train on earlier data, test on the most recent period). No random shuffling.
- **Baseline:** `<persistence / seasonal naive>`
- **Model:** `<e.g. Random Forest / Ridge on lag features>`
- **Metrics:** MAE and RMSE for baseline vs model.
- **Results:** `<paste actual MAE/RMSE from your notebook>`
- **Uncertainty:** forecast range derived from test-set residuals (`<e.g. 10th–90th percentile>`).
- **Risk tier:** a rule-based heuristic on forecast values using `<AQI category thresholds>`. It is not a validated probability.
- **Leakage control:** features use only information available at forecast time.

Full analysis: `notebooks/<notebook_name>.ipynb`

## 5. Data

Full details are in [`DATA_STATEMENT.md`](DATA_STATEMENT.md).

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
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

- No API keys, passwords or private data are needed to run the demo.
- Processed data is included in `data/processed/` so the app runs without re-downloading. To rebuild from raw files, see `<notebook or script>`.

## 7. Project structure

```
citypulse/
  app.py                 # Streamlit dashboard
  src/                   # data loading, features, modelling helpers
  notebooks/             # EDA, baseline, model, evaluation
  data/raw/              # original downloads (if licence allows redistribution)
  data/processed/        # cleaned data used by the app
  DATA_STATEMENT.md
  requirements.txt
  README.md
```

## 8. Limitations

Keep this honest and specific. Examples to adapt to what you actually found:

- Coverage gaps: `<stations with missing periods, how you handled them>`
- Station readings may not represent every neighbourhood.
- No ground-truth health outcomes, so the risk tier is a heuristic.
- Correlation in the analysis does not establish causation.
- Forecast skill is `<better/similar/worse>` than the baseline on the test period.

## 9. Responsible use

CityPulse is an educational prototype, not an emergency-warning system. Recommendations should be treated as prompts for expert review. No personal or sensitive data is used or published.

## 10. AI assistance and third-party components

- **AI assistance:** `<describe, e.g. AI assistant used for planning, code drafting and README drafting; all code and results were reviewed, run and are understood by the team>`
- **Open-source libraries:** pandas, NumPy, scikit-learn, Streamlit, Plotly, `<others>` — used under their respective licences.
- **Data and map attribution:** `<e.g. source names; OpenStreetMap contributors if maps are used>`

## 11. Team

Team of three. Update with names and roles.

| Member | Role |
|---|---|
| Ratnesh Pathak | Lead — data, analysis, modelling |
| `<Member 2>` | `<role>` |
| `<Member 3>` | `<role>` |

## 12. Hackathon

HackAMatch 1.0 — Data Mavericks × NSDC. Problem statement: *CityPulse*.