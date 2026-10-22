# CityPulse submission guide

This package follows the CityPulse problem statement's required submission items and its 100-point rubric. The demo is a historical replay based on 2021–2023 data.

## Run the core demo

From the repository root with Python 3.10 or later:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The bundled processed files let judges open the dashboard without an API key. To rebuild the core analysis from the bundled raw AQI and weather files:

```powershell
python -m src.clean.clean_pipeline
python -m src.features.eda_analysis
python -m src.features.build_features
python -m src.models.train_evaluate
python -m src.models.prioritization
```

On Linux or macOS, activate the virtual environment with `source venv/bin/activate`. The first rebuild can take several minutes.

## Submission files

| Brief requirement | File |
| --- | --- |
| Working decision interface | `app.py` |
| Source and setup | `README.md`, `requirements.txt`, `src/` |
| Data statement and source audit | `DATA_STATEMENT.md`, `DATA_SOURCES.md` |
| EDA, method, evaluation, limitations | `reports/eda_findings.md`, `reports/EVALUATION.md` |
| Five-minute presentation | `reports/slides/output/CityPulse_finalist_deck.pptx`, `DEMO_SCRIPT.md` |
| Backup visuals | `reports/figures/` |

## Judge demonstration sequence

1. Read the historical replay banner. The decision uses data through 30 December 2023 and estimates risk for 31 December 2023.
2. Select Chembur and inspection capacity of five. Show the rank, prior-day AQI, seven-day exposure, target-day risk estimate, and action dossier.
3. Change the policy weights so judges can see ranking sensitivity.
4. Show the seasonal chart and the 2023 holdout diagnostics. State that persistence has lower citywide point MAE than gradient boosting.
5. Close with the limits: point monitors, false alerts, undercovered intervals, and historical data.

## Rubric evidence

| Criterion (points) | Show judges |
| --- | --- |
| Problem framing (10) | The five-zone municipal inspection decision and named officer user |
| Data, cleaning, EDA (20) | Bundled AQI and weather files, quality report, and three measured findings |
| Method (15) | Persistence baseline, classifier, and explicit priority weights |
| Evaluation and integrity (15) | Chronological 2023 holdout, lower persistence MAE, precision and recall, interval undercoverage |
| UI and decision usefulness (20) | Station selection, capacity control, ranked roster, evidence, and action dossier |
| Explainability and limits (10) | Score components, caveats, sensor siting, and historical replay label |
| Reproducibility (5) | Offline rebuild commands and no key needed for the core demo |
| Presentation (5) | Six-slide deck, five-minute script, and backup figures |

## Checks before public submission

- Verify the licence and redistribution terms of the CPCB mirror and the bulletin mirror. The bundled copy supports local judging; its public redistribution terms remain unresolved in `DATA_SOURCES.md`.
- Verify official organiser deadline, archive format, team-size rules, and presentation slot; those details are not in the supplied problem statement.
- The four-station 2025–2026 pollutant notebook is supplementary because its raw Excel exports are absent. Do not use its numbers as the reproducible core claim.
- Keep the dashboard described as a historical replay until a fresh-data pipeline and prospective validation exist.
