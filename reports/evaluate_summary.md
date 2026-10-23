# Analytical Evaluation & Final Showcase Summary — CityPulse: Mumbai

**Date of Execution:** 2026-10-24 01:06:59 IST  
**Evaluator Script:** `Evaluate.py`  
**System Framing:** Operational screening and municipal resource prioritization prototype (BMC / MPCB). Not an official warning system.

---

## 1. Executive Showcase Scorecard

| Evaluation Dimension | Metric / Finding | Status / Standard |
| :--- | :--- | :--- |
| **Test Suite Execution** | 40 / 40 Passed | PASS |
| **Leakage & Data Integrity** | 6 / 6 Checks Passed | PASS |
| **CV Model Winner (2021-2022)** | LightGBM_L1_Residual (MAE: 22.99) | +3.9% Skill vs Persist |
| **2023 Holdout MAE (Prior Views Disclosed)** | 18.83 vs 19.42 (Persist) | BEATS PERSISTENCE |
| **Severe Episode (AQI > 200)** | Recall=0.870, PR-AUC=0.812 | Brier=0.0758 |
| **80% Prediction Interval** | Empirical Coverage: 73.8% | Below nominal coverage |
| **Weekly Backtest Lift** | +42.9% vs Uniform-Random Expectation | -1.9% vs Persist |
| **Policy Robustness** | 5 Zones Stable in Top 5 | 100 Monte Carlo Runs |

---

## 2. Environment & Dataset Provenance
- **Python / Runtime:** 3.13.7 on win32 (Seed: 42)
- **Deduplicated Hourly AQI Records:** 597,912
- **Hourly Weather Observations:** 26,280
- **Active Monitoring Stations:** 36 / 30
- **Evaluation Windows:** Train/CV: 2021-01-01 to 2022-12-31 | Holdout: 2023-01-01 to 2023-12-31

---

## 3. Test Suite & Leakage Audit
- **Unit & Integration Tests:** 40 / 40 passed (4.48s).
- **Leakage Controls:** Zero same-day lookahead verified across lags, rolling statistics, and expanding means.
- **Split Monotonicity:** Train dates strictly precede test dates in every fold. Zero shuffle leakage.

---

## 4. Cross-Validation Model Selection (2021–2022 Only)
- **Outer Splits:** 3 expanding date-based folds.
- **Configurations Evaluated:** 5 candidate models.
- **Winning Architecture:** `LightGBM_L1_Residual`
- **OOF MAE:** 22.989 (+3.87% skill vs persistence)
- **Paired Date-Block 95% CI:** [-1.562, -0.311] (Resampling unit: date)

---

## 5. Final Holdout Evaluation (2023 Forward Benchmark)
- **Point MAE:** Model = 18.83 vs Persistence = 19.42
- **Date-Resampled 95% CI on MAE Difference:** [-1.00, -0.07] (all station rows on a sampled date are resampled together).
- **Dynamic Statistical Verdict:** Model is **BEATS PERSISTENCE**.
- **Station Superiority:** Best model beats persistence on 23 of 29 active stations.
- *Note:* Holdout dataset was viewed during earlier development.

---

## 6. Severe-Episode Classification & Reliability Diagnostics
- **Severe Episode (AQI > 200) Recall:** 0.870 (vs Persistence: 0.717)
- **PR-AUC / ROC-AUC:** 0.812 / 0.955
- **Brier Score Loss:** 0.0758
- **Capacity-Matched Threshold:** At top-16.7% capacity, threshold is 0.655 (Precision: 0.689, Recall: 0.774)

---

## 7. Prediction Intervals (Quantile Regression)
- **Nominal Coverage:** 80.0% ([p10, p90] interval)
- **Empirical Holdout Coverage:** 73.8% (Mean width: 55.6 AQI units)
- **Honest Note:** HONEST ASSESSMENT: Empirical coverage (73.8%) falls short of the nominal 80.0% target by 6.2 percentage points. The intervals should be treated as an exploratory screening range rather than a guaranteed calibrated confidence bound.

---

## 8. Decision Backtest (Weekly Resource Allocation)
- **Backtest Period:** 51 weekly simulated cycles across 2023.
- **Lift vs Uniform-Random Expectation:** **+42.9%** (95% CI: [+30.3%, +60.2%])
- **Lift vs Persistence-Ranked:** **-1.9%** (95% CI: [-5.4%, +1.7%])
- **Lift vs Last-Week-Worst:** **-6.0%** (95% CI: [-11.9%, -0.3%])

---

## 9. Priority Score Robustness
- **Monte Carlo Simulations:** 100 runs under ±30% random weight perturbations.
- **Robust Core:** 5 monitoring stations maintain ≥90% probability of remaining in the top 5.

---

## 10. Judge Q&A Cheat Sheet

### Q: How did you split the data?
**A:** Strictly chronological date-based splits. CV was trained strictly on 2021–2022 using 3 expanding folds (Fold 1: 12m train/4m test, Fold 2: 16m train/4m test, Fold 3: 20m train/4m test). The entire year 2023 was held out as a forward benchmark.

### Q: How do you prevent temporal leakage?
**A:** Every feature is constructed at decision time (23:59 on Day t-1): lags shift by 1+ days, rolling windows end at t-1, weather uses prior-day telemetry, and station expanding means are shifted by 1 day. In all folds, max(train_date) < min(test_date) is verified by assertion.

### Q: Why does persistence matter so much?
**A:** Ambient urban air quality is highly autoregressive. Yesterday's concentration (lag-1) already accounts for localized topography, baseline traffic, and microclimates. Any model claiming 90%+ accuracy without benchmarking against lag-1 is misrepresenting trivial autoregression as predictive skill.

### Q: Does your machine learning model beat persistence?
**A:** On pure holdout point MAE, our model achieves 18.83 vs persistence's 19.42. The 95% bootstrap confidence interval demonstrates that the point forecast beats persistence. However, ML provides crucial value in non-linear probabilistic classification.

### Q: What does machine learning add if point MAE is close?
**A:** ML adds probabilistic risk screening (Recall 0.870, PR-AUC 0.812) and exploratory 80% quantile ranges. Those ranges have not met their nominal coverage target.

### Q: How reliable are the prediction intervals?
**A:** Nominal 80% quantile intervals achieve 73.8% empirical coverage in 2023. Per-season coverage is shown in the evaluation output; these intervals are exploratory until calibrated.

### Q: How many model configurations were tried?
**A:** We evaluated 5 distinct configurations in Phase 1b CV, including Ridge with inner-date-split alpha tuning, HistGradientBoosting, LightGBM (L1 and Huber objectives), persistence-residual formulations, and per-station models with pooled fallbacks.

### Q: What are the known limitations?
**A:** 1. Persistence is a strong baseline; additional local measurements may improve forecasts. 2. Station coverage is uneven. 3. This is a decision-support prototype, not a statutory warning system.

---

## 11. Known Limitations & Responsible Deployment
1. **Autoregressive Baseline:** Point forecast improvements over persistence are modest on citywide averages.
2. **Spatial Density:** Official CAAQMS coverage is uneven; station readings do not represent entire wards.
3. **Sensor Attrition:** Periodic hardware outages require robust imputation to prevent ranking distortion.
4. **Administrative Role:** CityPulse is a decision-support screener for municipal inspectors, not an automated penal enforcement tool.
