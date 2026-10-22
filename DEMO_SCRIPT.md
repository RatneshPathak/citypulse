# CityPulse: 5-minute finalist presentation

## 0:00–0:30 | The decision

“A municipal officer has capacity to inspect five air-quality zones. CityPulse helps choose where to look first and shows the evidence behind that choice. This is an offline historical replay for Mumbai, not a live warning system.”

## 0:30–1:15 | Data and strongest finding

“The bundled 2021–2023 data contains 597,912 deduplicated hourly AQI records across 36 station labels, plus 26,280 hourly weather observations. We require at least 18 valid AQI hours for a station-day; 22,608 days pass that project rule. Mean AQI is 63.9 in monsoon months and 185.0 in winter months. Uneven coverage and station siting limit citywide interpretation.”

Show the seasonal chart in the Discover tab. The 2025–2026 four-station pollutant notebook is supplementary because its raw Excel exports are not bundled.

## 1:15–2:00 | Method and validation

“We trained on 2021–2022 and reserved 2023 as a chronological holdout. Inputs use only prior-day observations and calendar or station information. The persistence baseline has 19.42 MAE; gradient boosting has 20.33. We therefore keep persistence as the point-estimate benchmark. For AQI above 200, the classifier reaches 87.7% recall and 59.2% precision. Its nominal 80% interval covers 74.1% of holdout outcomes, so we display that limitation.”

## 2:00–4:30 | Live product demo

1. Open the dashboard and read the replay banner: observations through 30 December 2023, target day 31 December 2023.
2. In Risk Prioritisation, set inspection capacity to five and show the ranked roster. Select Chembur. Explain its observed prior-day AQI, seven-day exposure, estimated target-day risk, and recommended inspection. The score is a heuristic for triage, not proof of an emission source.
3. Adjust the exposure and risk weights. Show how the rank changes and explain that the policy choice is visible to the officer.
4. Open Discover for the seasonal and station patterns, then Forecast & Risk Calibration for the 2023 holdout comparison. Point to precision, recall, and interval undercoverage before returning to the action dossier.

If the app stalls, use the backup figures in `reports/figures/` and the tables in `reports/eda_findings.md` and `reports/EVALUATION.md`.

## 4:30–5:00 | Limits and next step

“The dashboard replays 2023 and must not be used for current alerts. Station readings can miss street-level variation; the classifier produces false positives, and the uncertainty interval undercovers. The next step is a prospective pilot with fresh regulatory observations, documented retrieval logs, and officer feedback on whether the ranked inspections find actionable problems.”

## Judge Q&A facts

- **Why a simple baseline?** Persistence has the lowest citywide MAE on the holdout.
- **Is the 18-hour rule official CPCB policy?** We use it as a project threshold; the report does not establish it as the regulatory requirement.
- **Is the probability calibrated?** No separate calibration fit was performed. We report holdout Brier score and a reliability diagram without claiming calibration.
- **Can judges reproduce the demo without a key?** Yes, from bundled data and `make all`; source mirror terms and the supplementary Excel exports still need independent verification before publication.
