# Phase 1b CV-only evaluation (2021–2022)

Three expanding outer folds; Ridge alpha is tuned on inner date splits inside each outer training fold.

Bootstrap resamples dates (all station rows for a sampled date together); 2,000 replicates, seed 42.

Candidate configurations: 10 total, including 5 LightGBM variants. Parameters were fixed before results were viewed.

Retained Phase 1a groups: recent_change, station_history.

## Ablation

| group | features | MAE | alpha_by_fold |
| --- | --- | --- | --- |
| old | 28 | 23.316 | [0.1, 0.1, 0.1] |
| long_history | 31 | 23.379 | [0.1, 0.1, 0.1] |
| recent_change | 30 | 23.277 | [0.1, 0.1, 0.1] |
| station_history | 29 | 23.247 | [0.1, 0.1, 0.1] |
| calendar | 30 | 23.412 | [100.0, 100.0, 100.0] |


## Pooled

| model | n | MAE | skill_pct | date_bootstrap_CI_MAE_diff |
| --- | --- | --- | --- | --- |
| Persistence | 6418 | 23.915 | 0.0 | [0.0, 0.0] |
| Ridge | 6418 | 23.208 | 2.96 | [-1.513, 0.104] |
| HistGB_L1 | 6418 | 24.309 | -1.65 | [-0.626, 1.423] |
| LightGBM_L1 | 6418 | 23.396 | 2.17 | [-1.374, 0.324] |
| LightGBM_Huber | 6418 | 58.301 | -143.79 | [31.325, 37.559] |
| Ridge_Residual | 6418 | 23.156 | 3.17 | [-1.54, 0.041] |
| HistGB_L1_Residual | 6418 | 23.429 | 2.03 | [-1.352, 0.316] |
| LightGBM_L1_Residual | 6418 | 22.989 | 3.87 | [-1.643, -0.234] |
| LightGBM_Huber_Residual | 6418 | 23.67 | 1.02 | [-0.315, -0.174] |
| PerStation_LightGBM_L1 | 6418 | 26.256 | -9.79 | [1.285, 3.394] |


## Per fold

| fold | model | n | MAE | skill_pct |
| --- | --- | --- | --- | --- |
| Fold 1 (test 2022-Q1/Q2) | Persistence | 2162 | 31.861 | 0.0 |
| Fold 2 (test 2022-Q2/Q3) | Persistence | 2037 | 16.361 | 0.0 |
| Fold 3 (test 2022-Q3/Q4) | Persistence | 2219 | 23.106 | 0.0 |
| Fold 1 (test 2022-Q1/Q2) | Ridge | 2162 | 30.009 | 5.82 |
| Fold 2 (test 2022-Q2/Q3) | Ridge | 2037 | 16.267 | 0.57 |
| Fold 3 (test 2022-Q3/Q4) | Ridge | 2219 | 22.953 | 0.66 |
| Fold 1 (test 2022-Q1/Q2) | HistGB_L1 | 2162 | 31.474 | 1.22 |
| Fold 2 (test 2022-Q2/Q3) | HistGB_L1 | 2037 | 18.266 | -11.64 |
| Fold 3 (test 2022-Q3/Q4) | HistGB_L1 | 2219 | 22.877 | 0.99 |
| Fold 1 (test 2022-Q1/Q2) | LightGBM_L1 | 2162 | 30.317 | 4.85 |
| Fold 2 (test 2022-Q2/Q3) | LightGBM_L1 | 2037 | 16.871 | -3.11 |
| Fold 3 (test 2022-Q3/Q4) | LightGBM_L1 | 2219 | 22.642 | 2.01 |
| Fold 1 (test 2022-Q1/Q2) | LightGBM_Huber | 2162 | 53.031 | -66.44 |
| Fold 2 (test 2022-Q2/Q3) | LightGBM_Huber | 2037 | 58.16 | -255.48 |
| Fold 3 (test 2022-Q3/Q4) | LightGBM_Huber | 2219 | 63.567 | -175.1 |
| Fold 1 (test 2022-Q1/Q2) | Ridge_Residual | 2162 | 29.897 | 6.16 |
| Fold 2 (test 2022-Q2/Q3) | Ridge_Residual | 2037 | 16.259 | 0.62 |
| Fold 3 (test 2022-Q3/Q4) | Ridge_Residual | 2219 | 22.918 | 0.81 |
| Fold 1 (test 2022-Q1/Q2) | HistGB_L1_Residual | 2162 | 30.582 | 4.02 |
| Fold 2 (test 2022-Q2/Q3) | HistGB_L1_Residual | 2037 | 17.279 | -5.61 |
| Fold 3 (test 2022-Q3/Q4) | HistGB_L1_Residual | 2219 | 22.104 | 4.34 |
| Fold 1 (test 2022-Q1/Q2) | LightGBM_L1_Residual | 2162 | 29.752 | 6.62 |
| Fold 2 (test 2022-Q2/Q3) | LightGBM_L1_Residual | 2037 | 16.525 | -1.0 |
| Fold 3 (test 2022-Q3/Q4) | LightGBM_L1_Residual | 2219 | 22.334 | 3.34 |
| Fold 1 (test 2022-Q1/Q2) | LightGBM_Huber_Residual | 2162 | 31.469 | 1.23 |
| Fold 2 (test 2022-Q2/Q3) | LightGBM_Huber_Residual | 2037 | 16.224 | 0.84 |
| Fold 3 (test 2022-Q3/Q4) | LightGBM_Huber_Residual | 2219 | 22.908 | 0.86 |
| Fold 1 (test 2022-Q1/Q2) | PerStation_LightGBM_L1 | 2162 | 32.761 | -2.82 |
| Fold 2 (test 2022-Q2/Q3) | PerStation_LightGBM_L1 | 2037 | 18.411 | -12.53 |
| Fold 3 (test 2022-Q3/Q4) | PerStation_LightGBM_L1 | 2219 | 27.121 | -17.37 |


## Per season

| season | model | n | MAE | skill_pct |
| --- | --- | --- | --- | --- |
| monsoon | Persistence | 1988 | 12.467 | 0.0 |
| post_monsoon | Persistence | 1158 | 24.461 | 0.0 |
| summer | Persistence | 1661 | 26.827 | 0.0 |
| winter | Persistence | 1611 | 34.646 | 0.0 |
| monsoon | Ridge | 1988 | 12.747 | -2.25 |
| post_monsoon | Ridge | 1158 | 23.722 | 3.02 |
| summer | Ridge | 1661 | 24.62 | 8.23 |
| winter | Ridge | 1611 | 34.292 | 1.02 |
| monsoon | HistGB_L1 | 1988 | 13.511 | -8.37 |
| post_monsoon | HistGB_L1 | 1158 | 23.428 | 4.22 |
| summer | HistGB_L1 | 1661 | 26.91 | -0.31 |
| winter | HistGB_L1 | 1611 | 35.587 | -2.72 |
| monsoon | LightGBM_L1 | 1988 | 12.82 | -2.83 |
| post_monsoon | LightGBM_L1 | 1158 | 23.321 | 4.66 |
| summer | LightGBM_L1 | 1661 | 25.348 | 5.51 |
| winter | LightGBM_L1 | 1611 | 34.487 | 0.46 |
| monsoon | LightGBM_Huber | 1988 | 60.512 | -385.38 |
| post_monsoon | LightGBM_Huber | 1158 | 54.932 | -124.57 |
| summer | LightGBM_Huber | 1661 | 45.312 | -68.9 |
| winter | LightGBM_Huber | 1611 | 71.388 | -106.05 |
| monsoon | Ridge_Residual | 1988 | 12.73 | -2.11 |
| post_monsoon | Ridge_Residual | 1158 | 23.661 | 3.27 |
| summer | Ridge_Residual | 1661 | 24.603 | 8.29 |
| winter | Ridge_Residual | 1611 | 34.165 | 1.39 |
| monsoon | HistGB_L1_Residual | 1988 | 13.157 | -5.54 |
| post_monsoon | HistGB_L1_Residual | 1158 | 23.373 | 4.45 |
| summer | HistGB_L1_Residual | 1661 | 25.557 | 4.74 |
| winter | HistGB_L1_Residual | 1611 | 33.95 | 2.01 |
| monsoon | LightGBM_L1_Residual | 1988 | 12.512 | -0.36 |
| post_monsoon | LightGBM_L1_Residual | 1158 | 23.561 | 3.68 |
| summer | LightGBM_L1_Residual | 1661 | 25.14 | 6.29 |
| winter | LightGBM_L1_Residual | 1611 | 33.288 | 3.92 |
| monsoon | LightGBM_Huber_Residual | 1988 | 12.339 | 1.03 |
| post_monsoon | LightGBM_Huber_Residual | 1158 | 24.227 | 0.95 |
| summer | LightGBM_Huber_Residual | 1661 | 26.549 | 1.04 |
| winter | LightGBM_Huber_Residual | 1611 | 34.286 | 1.04 |
| monsoon | PerStation_LightGBM_L1 | 1988 | 14.765 | -18.43 |
| post_monsoon | PerStation_LightGBM_L1 | 1158 | 26.464 | -8.19 |
| summer | PerStation_LightGBM_L1 | 1661 | 27.489 | -2.47 |
| winter | PerStation_LightGBM_L1 | 1611 | 39.017 | -12.62 |


CV-selected model: **LightGBM_L1_Residual**. The 2023 holdout has not been run for Phase 1b.
