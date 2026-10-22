# Notebook Audit: `src/CityPulse_AQI_Cleaning_EDA.ipynb`

> **Built for HackAMatch 1.0 by Ratnesh, Rishi & Shreya**  
> **Audit Date:** 22 October 2026  
> **Source Notebook:** `src/CityPulse_AQI_Cleaning_EDA.ipynb` (25 code cells, Google Colab runtime)  
> **Audit Status:** Complete static & runtime execution analysis.

---

## 1. Executive Summary

The notebook `CityPulse_AQI_Cleaning_EDA.ipynb` represents the team's core empirical analysis and data cleaning workflow for continuous ambient air quality in Mumbai. It ingests hourly multi-pollutant measurements from the official Central Pollution Control Board (CPCB) portal for **4 continuous monitoring stations** across a **22-month observation window** (1 January 2025 to 22 October 2026).

The cleaning methodology is scientifically sound and conservative:
1. It parses proprietary CPCB multi-row Excel headers accurately.
2. It enforces numeric data typing and date parsing.
3. It detects and removes 15.8% of records where sensors were completely offline (all pollutants NaN).
4. It detects and quantifies statistical outliers using station-specific IQR bounds without silently dropping real-world pollution shocks.

---

## 2. Input Data & Source Files

The notebook loads raw Excel files using `glob.glob('/content/*.xlsx')`. Based on execution metadata in Cells 1–4, 8 files were processed:

| # | Filename | Station Extracted (`row 5, col 2`) | Period (`From` → `To`) | Rows | Valid Timestamps |
|---|---|---|---|---|---|
| 1 | `Advance_Search_1792671763347.xlsx` | **Bandra Kurla Complex, Mumbai - IITM** | 2025-01-01 → 2025-12-31 | 8,736 | 100% |
| 2 | `Advance_Search_1792672262632.xlsx` | **Bandra Kurla Complex, Mumbai - IITM** | 2026-01-01 → 2026-10-22 | 7,056 | 100% |
| 3 | `Advance_Search_1792672709872.xlsx` | **Borivali East, Mumbai - MPCB** | 2025-01-01 → 2025-12-31 | 8,736 | 100% |
| 4 | `Advance_Search_1792672943405.xlsx` | **Borivali East, Mumbai - MPCB** | 2026-01-01 → 2026-10-22 | 7,056 | 100% |
| 5 | `Advance_Search_1792673175387.xlsx` | **Chembur, Mumbai - MPCB** | 2025-01-01 → 2025-12-31 | 8,736 | 100% |
| 6 | `Advance_Search_1792673076381.xlsx` | **Chembur, Mumbai - MPCB** | 2026-01-01 → 2026-10-22 | 7,056 | 100% |
| 7 | `Advance_Search_1792673241762.xlsx` | **Siddharth Nagar-Worli, Mumbai - IITM** | 2025-01-01 → 2025-12-31 | 8,736 | 100% |
| 8 | `Advance_Search_1792673310690.xlsx` | **Siddharth Nagar-Worli, Mumbai - IITM** | 2026-01-01 → 2026-10-22 | 7,056 | 100% |
| **Total** | **8 files** | **4 unique stations** | **2025-01-01 → 2026-10-22** | **63,168** | **0 duplicate timestamps** |

### File Format Characteristics:
- **Header Structure:** First 10 rows contain CPCB organizational and station metadata. Row index 10 (11th Excel row) contains column names: `From Date`, `To Date`, `PM2.5`, `PM10`, `NO`, `NO2`, `NH3`, `SO2`, `CO`, `OZONE`.
- **Measurement Units:** `PM2.5` ($\mu g/m^3$), `PM10` ($\mu g/m^3$), `NO` ($\mu g/m^3$), `NO2` ($\mu g/m^3$), `NH3` ($\mu g/m^3$), `SO2` ($\mu g/m^3$), `CO` ($mg/m^3$).
- **Path Dependency:** Hardcoded to Google Colab's virtual filesystem (`/content/*.xlsx`).

---

## 3. Cleaning Steps in Order of Execution

```
[ Raw Excel Files ]
       │
       ▼
1. Metadata & Header Extraction (Cell 4: header=10, station metadata from row 5)
       │
       ▼
2. Timestamp Standardization (Cell 4: dayfirst=True, format YYYY-MM-DD HH:MM:SS)
       │
       ▼
3. Numeric Coercion (Cell 4: pd.to_numeric(errors='coerce') across all 7 pollutants)
       │
       ▼
4. Deduplication & Integrity Verification (Cell 5: 0 duplicates on ['Station', 'From Date', 'To Date'])
       │
       ▼
5. Offline Sensor Filtering (Cell 8: Drop rows where ALL 7 pollutants are NaN -> 9,981 rows removed)
       │
       ▼
6. Outlier Diagnostics (Cell 17–18: Tukey IQR 1.5x bounds flagged; preserved in dataset)
       │
       ▼
7. Feature Projection & Clean Export (Cell 21: 10 canonical columns saved to CSV)
```

### Detailed Transformations:
1. **Deduplication:** Tested in Cell 5. Zero duplicate timestamps within stations.
2. **Missing Value Treatment:**
   - Pre-filter: 63,168 total hourly rows.
   - Filter rule: `all_missing = df[['PM2.5', 'PM10', 'NO', 'NO2', 'NH3', 'SO2', 'CO']].isna().all(axis=1)`
   - Filter impact: 9,981 rows (15.80%) removed where all pollutant telemetry was blank.
   - Post-filter: **53,187 rows retained**.
   - Partial NaNs are **strictly preserved** (not imputed with synthetic averages), maintaining data integrity.
3. **Outlier Treatment:**
   - Outliers are computed per station using $IQR = Q_3 - Q_1$:
     - Bounds: $[Q_1 - 1.5 \times IQR, \quad Q_3 + 1.5 \times IQR]$
   - 1,281 potential PM2.5 outlier readings identified (2.41% of valid PM2.5 readings).
   - In accordance with best environmental data science practices, **outliers are NOT dropped**. They are preserved because extreme values in urban air quality frequently reflect true physical events (e.g., post-monsoon crop burning, industrial venting, Diwali fireworks, temperature inversions).

---

## 4. EDA Findings: Real Findings vs. Scratch Work

### A. Validated Analytical Findings (Keep in App & Reports)

| Finding | Code Cell | Evidence / Supporting Metric | Physical & Operational Meaning |
|---|---|---|---|
| **1. Spatial Hierarchy & Hotspots** | Cell 9, 10 | • **BKC:** Highest mean PM2.5 (33.50 $\mu g/m^3$) & PM10 (101.06 $\mu g/m^3$)<br>• **Chembur:** PM2.5 (30.21 $\mu g/m^3$), PM10 (75.92 $\mu g/m^3$)<br>• **Worli:** PM2.5 (29.30 $\mu g/m^3$), PM10 (79.81 $\mu g/m^3$)<br>• **Borivali East:** Cleanest (PM2.5 23.61 $\mu g/m^3$, PM10 62.76 $\mu g/m^3$) | BKC and Chembur are heavy transit and industrial chokepoints. Coastal ventilation lowers Worli's PM2.5, while Borivali benefits from National Park buffer. |
| **2. U-Shaped Seasonal Cycle** | Cell 11, 12, 13 | • **July–August Monsoon Washout:** PM2.5 drops to 10.4–12.9 $\mu g/m^3$ citywide.<br>• **Oct–Dec Winter Trapping:** Surges to 55.8–80.4 $\mu g/m^3$ (peaked Nov 2025 at BKC: 80.41 $\mu g/m^3$). | Heavy monsoon rains wash out aerosols; winter calm winds and low boundary layer trap emissions. |
| **3. Bimodal Diurnal Traffic Pulse** | Cell 19, 20 | • **Morning Peak:** 08:00–10:00 IST<br>• **Afternoon Dispersion Trough:** 14:00–16:00 IST<br>• **Night Stagnation Peak:** 20:00–23:00 IST | Morning traffic emits into a shallow boundary layer; solar heating expands boundary layer in afternoon; evening traffic + nocturnal inversion concentrates particulate. |
| **4. Hardware Failure & Sensor Drift** | Cell 7 | • **Worli SO2 Sensor:** 100.0% missing across entire 22 months (0 valid readings).<br>• **BKC Missing Block:** Jan–Apr 2025 experienced prolonged station downtime (4,966 all-NaN rows). | Critical regulatory caveat: CPCB stations have prolonged sensor-specific hardware outages. Multi-pollutant composite scores must handle sensor absence gracefully. |
| **5. Extreme Episodic Spikes** | Cell 15 | • **Chembur PM2.5 Spike:** 771.39 $\mu g/m^3$ on 2026-08-04 19:00.<br>• **BKC PM2.5 Spike:** 555.79 $\mu g/m^3$ on 2025-10-21 01:00.<br>• **BKC PM10 Spike:** 699.41 $\mu g/m^3$ on 2025-10-21 01:00. | Episodic local industrial venting or festival emissions can cause acute, localized 20x baseline shocks. |

### B. Exploratory Scratch Work (To Refactor / Clean Up)
- **Cell 0:** `os.listdir('/content')` (Scratch directory check).
- **Cell 1–3:** Diagnostic loops reading first 3 to 25 rows of each Excel file (pre-development exploratory inspection).
- **Cell 11 vs 12 vs 13:** Cells 11, 12, and 13 plot identical monthly PM2.5 trends with minor formatting tweaks (redundant code).
- **Cell 14 (Yearly average comparison):** Compares 2025 (12 months) vs 2026 (10 months). Because 2026 cuts off on October 22, it excludes the high-pollution months of November and December, creating a false impression that 2026 is significantly cleaner than 2025. This needs an explicit analytical caveat.
- **Cell 23, 24:** `from google.colab import files; files.download(...)` (Colab-specific artifact downloads).

---

## 5. Outputs Produced by the Notebook

1. **`citypulse_cleaned_data.csv`** (Primary Output):
   - Shape: (53,187 rows, 10 columns)
   - Columns: `From Date`, `To Date`, `Station`, `PM2.5`, `PM10`, `NO`, `NO2`, `NH3`, `SO2`, `CO`
2. **`citypulse_station_summary.csv`**:
   - Multi-pollutant descriptive stats (mean, median, min, max, count) per station.
3. **Auxiliary Exports**:
   - `mumbai_pollution_combined.csv` (raw combined, 63,168 rows)
   - `cpcb_file_summary.csv` (ingestion report)
   - `station_pollution_statistics.csv`
   - `station_mean_pm25_pm10.csv`
   - `monthly_pm25_trends.csv`
   - `yearly_pm25_comparison.csv`
   - `pm25_potential_outliers.csv` (1,281 flagged rows)
   - `pm25_outlier_summary.csv`
   - `hourly_pm25_patterns.csv`
   - `hourly_pm10_patterns.csv`

---

## 6. Code Defects, Leakage, and Open Questions

### Potential Problems Identified:
1. **Machine-Specific Pathing:** All file reads and writes use `/content/` paths hardcoded to Google Colab.
2. **Missing Raw Files in Workspace:** The 8 Excel files (`Advance_Search_*.xlsx`) were uploaded directly to Google Colab and are not currently checked into the local `data/raw/` repository directory.
3. **Timezone Handling:** Timestamps in `From Date` are parsed without explicit timezone localization (`tz_localize('Asia/Kolkata')`).
4. **Duplicate Execution Cells:** Cells 11, 12, 13 duplicate the monthly trend aggregation and plotting.
5. **No Data Leakage:** Because the notebook performs purely unsupervised data hygiene and descriptive EDA (no train/test split or predictive models trained here), there is **zero risk of data leakage** in this notebook.

---

## 7. Refactoring & Integration Plan

To integrate this notebook smoothly into the CityPulse architecture while keeping the notebook intact:

1. **Modular Cleaning Function (`src/clean/aqi_cleaning.py`):**
   - Extract the cleaning logic into a pure, testable function `clean_cpcb_excel_files(input_dir, output_path)` that handles CPCB Excel headers, converts dates, drops all-NaN rows, flags IQR outliers, and writes standard parquet/csv outputs to `data/processed/`.
2. **Reusable EDA Visualisations (`src/eda/visualizations.py`):**
   - Refactor the 5 core charts (Station Means, Monthly Trends, Hourly Diurnal Cycles, Boxplot Distributions, Outlier Summaries) into modular functions that return matplotlib/plotly figures.
3. **Thin Narrative Notebook:**
   - Clean up `src/CityPulse_AQI_Cleaning_EDA.ipynb` into a clean, top-to-bottom executable narrative importing from `src/clean/` and `src/eda/`.
4. **Data Bridge & Single Source of Truth:**
   - Link the cleaned output to the modelling pipeline and Streamlit dashboard.
   - Surface the key EDA findings (Diurnal Peaks, Seasonal U-Curve, Sensor Failure at Worli) in Tab 2 and Tab 5 of the dashboard with explicit caveats.
