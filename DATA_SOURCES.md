Data sources audit improved · MD

# Data Sources & Discovery Audit — CityPulse: Mumbai

|                  |                                                                                                                                                                |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Audit date**   | 22 October 2026                                                                                                                                                |
| **Scope**        | Mumbai Metropolitan Region (MMR), India                                                                                                                        |
| **Policy**       | Free, public data only: no paid APIs, no subscriptions, no credit card. Free API keys are avoided so the project runs from a fresh clone with no registration. |
| **Audit status** | Source access verified on the date above. Items marked **[verify]** need a human check before publication.                                                     |

---

## 1. Summary

The reproducible 2021–2023 core uses bundled CPCB AQI, Open-Meteo weather, and a partial OpenStreetMap context table. CPCB bulletins and a later pollutant notebook are supplementary. The licence and terms for third-party mirrors remain to be verified before public submission.

| Role                   | Source                         | Key needed          | Decision                     |
| ---------------------- | ------------------------------ | ------------------- | ---------------------------- |
| Hourly AQI            | CPCB CAAQMS historical archive | No                  | **USED**                     |
| Regulatory context    | CPCB daily AQI bulletins       | No                  | SUPPLEMENTARY                |
| Weather drivers        | Open-Meteo Historical Archive  | No                  | **USED**                     |
| Spatial context        | OpenStreetMap (Overpass)       | No                  | **USED**                     |
| Alternative AQ API     | OpenAQ v3 REST                 | Yes                 | REJECTED                     |
| Alternative AQ bulk    | OpenAQ S3 archive              | No                  | REJECTED                     |
| Live AQ portal         | CPCB CCR portal                | No (session tokens) | REJECTED                     |
| Government API         | data.gov.in real-time          | Yes                 | REJECTED (optional fallback) |
| Alternative weather    | NASA POWER / IMD               | No                  | REJECTED                     |

---

## 2. Source Inventory and Decision Table

### 2.1 Sources used

| Source                                     | Provider / endpoint                                                 | Licence / terms                                                                                                        | Coverage                                                                                              | Role                                                          |
| ------------------------------------------ | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| **CPCB CAAQMS historical station archive** | CPCB data, accessed through the open mirror `Vonter/india-cpcb-aqi` | Government of India open data. Mirror licence and redistribution terms **[verify]** | 38 source station names in Mumbai-area raw data; 36 canonical labels in the 2021–2023 processed data. Hourly AQI values, not pollutant concentrations. | Primary ground truth |
| **CPCB official daily AQI bulletins**      | CPCB / MoEFCC via `urbanemissionsinfo/AQI_bulletins`                | CC BY-SA 4.0 as stated by the repo **[verify]**. Share-alike applies to derivatives                                    | Daily AQI, prominent pollutant, station counts, Mumbai and Navi Mumbai, 2015–2025                     | Calibration and category validation only (not model features) |
| **Open-Meteo Historical Weather API**      | `archive-api.open-meteo.com`                                        | Data: CC BY 4.0. API: free tier is **non-commercial use only**, attribution required                                   | Bundled core weather: 26,280 hourly rows for 2021–2023 at one Mumbai point | Meteorological drivers |
| **OpenStreetMap via Overpass**             | `overpass-api.de`                                                   | ODbL 1.0, © OpenStreetMap contributors. Share-alike on derived databases                                               | Bundled static context table covers 18 stations | Partial land-use and road context |

### 2.2 Sources rejected

| Source                        | Reason rejected                                                                                                                                                                                                                 | Evidence           | Revisit if…                                                                |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | -------------------------------------------------------------------------- |
| **OpenAQ REST v3**            | Requires a free API key, which breaks the zero-registration rule. v1/v2 return HTTP 410                                                                                                                                         | HTTP 410 on v2     | Key requirement is dropped                                                 |
| **OpenAQ S3 bulk bucket**     | Partitioned by numeric location ID with no station-name lookup, so discovery is inefficient. Adds nothing over CPCB direct data                                                                                                 | Bucket structure   | A location-ID lookup table is published                                    |
| **CPCB CCR live portal**      | Exports capped at 7–30 days per query. Raw POST returns HTTP 405 without dynamic session tokens, so it is not reproducible by script                                                                                            | HTTP 405           | A stable bulk-export endpoint appears                                      |
| **data.gov.in real-time API** | Needs a free key. Frequent read timeouts (>30 s) under automated calls                                                                                                                                                          | ReadTimeout >30 s  | Reliability improves. Kept as optional fallback in `src/ingest/run_all.py` |
| **NASA POWER / IMD portal**   | Redundant: Open-Meteo already serves hourly reanalysis-based weather. (Note: Open-Meteo's archive is built on ERA5/ERA5-Land and similar reanalyses. It is not an IMD assimilation feed, so the earlier wording was corrected.) | Feature comparison | IMD station observations are needed as an independent check                |

---

## 3. Field Specifications and Transformations

### 3.1 Air quality (CPCB CAAQMS)

**Raw fields in the bundled core file:** `Station ID`, `Station Name`, `Date`, and hourly AQI columns `00:00:00`–`23:00:00`. Pollutant-specific concentrations belong to the separate notebook study; its Excel inputs are not bundled.

**Units:** PM and gases in µg/m³; CO in mg/m³ **[verify per column]**. Convert nothing silently, and record units in the schema.

**Geographic filter:** stations in Greater Mumbai and Navi Mumbai only. _Note:_ the scope line says "MMR", which also includes Thane, Kalyan-Dombivli and others. Either rename the scope to "Greater Mumbai + Navi Mumbai" or add those stations.

**Quality control, applied in this order:**

| Step            | Rule                                                                      | Action                           |
| --------------- | ------------------------------------------------------------------------- | -------------------------------- |
| 1. Range check  | PM2.5 ∈ [0, 1000]; PM10 ∈ [0, 2000]; NO2 ∈ [0, 500]; SO2 ∈ [0, 500] µg/m³ | Out-of-range → `NaN`             |
| 2. Negatives    | Any value < 0 (calibration drift / telemetry error)                       | → `NaN`                          |
| 3. Stuck sensor | ≥ 6 identical consecutive hourly readings                                 | → `NaN`                          |
| 4. Short gaps   | ≤ 2 consecutive missing hours                                             | Linear interpolation per station |
| 5. Long gaps    | > 2 consecutive hours                                                     | Left missing                     |
| 6. Daily mean   | Day valid only with enough hourly coverage                                | See note below                   |

> **Coverage threshold:** the document used 75% (≥ 18 h). CPCB's NAQI guidance, as I recall it, accepts a 24-hour average with **at least 16 valid hours**. Decide which you follow and state it. If you keep 18 h, call it a stricter project rule, not "CPCB guidelines". **[verify]**

**Also missing:** range limits for CO and Ozone, so add them. Log, per station, how many values each step removed.

### 3.2 Weather (Open-Meteo)

**Raw fields:** `temperature_2m` (°C), `relative_humidity_2m` (%), `dew_point_2m` (°C), `precipitation` (mm), `surface_pressure` (hPa), `wind_speed_10m` (km/h), `wind_direction_10m` (°), `shortwave_radiation` (W/m²).

**Transformations:**

- **Wind vector** (meteorological convention, direction the wind blows _from_):
  u = −speed · sin(dir), v = −speed · cos(dir). Interpret u/v as the sea-breeze vs land-breeze axis only after checking Mumbai's coastline orientation.
- **Time features:** hour, day of week, month, monsoon / non-monsoon flag, solar elevation computed from latitude, longitude and timestamp.
- **Stagnation / inversion proxy:** high surface pressure + low wind + high humidity + night-time. This is a _proxy_, not a measured boundary-layer height. Describe it that way in all outputs.
- **Time zone:** store everything in IST (UTC+5:30), or convert explicitly. Mixing UTC weather with IST station data silently shifts the diurnal cycle by 5.5 hours.
- **Spatial limitation:** one weather point is applied to all stations. This ignores microclimate differences across the city.

### 3.3 Spatial / OSM features

**Raw fields:** station lat/lon; counts of `highway` segments, `landuse=industrial`, `landuse=construction`, `leisure=park` within a 1.5 km buffer; coastal flag.

**Transformations:** per-buffer densities normalised by buffer area; binary coastal flag from distance to the Arabian Sea coastline.

**Caveats:** OSM is a snapshot and completeness varies. Construction tags especially go stale. Record the Overpass query date and the OSM planet timestamp.

### 3.4 CPCB Advance Search Multi-Pollutant Ground Truth (`src/CityPulse_AQI_Cleaning_EDA.ipynb`)

**Source & Scope:** Continuous hourly ambient telemetry downloaded from the CPCB CCR Advance Search portal for 4 representative Mumbai monitoring stations across a 22-month observation window (2025-01-01 to 2026-10-22):
1. **Bandra Kurla Complex, Mumbai - IITM** (Western Suburbs / Commercial Financial Center)
2. **Borivali East, Mumbai - MPCB** (Western Suburbs / SGNP Forest Perimeter)
3. **Chembur, Mumbai - MPCB** (Eastern Suburbs / Heavy Industrial Corridor)
4. **Siddharth Nagar-Worli, Mumbai - IITM** (South Mumbai / Coastal Commercial Transit)

**Raw Ingestion & Deduplication:**
- 8 raw Excel exports (1 annual 2025 file + 1 2026 YTD file per station).
- Total raw observations: 63,168 hourly rows (15,792 rows per station).
- Deduplication: Verified zero duplicate timestamps within any station.

**Missing Value Treatment:**
- **Offline Sensor Exclusion:** 9,981 rows (15.80% of total) where all 7 monitored pollutants (`PM2.5`, `PM10`, `NO`, `NO2`, `NH3`, `SO2`, `CO`) were simultaneously blank (`NaN`) were filtered out.
- **Analysis-Ready Sample:** 53,187 valid hourly records retained.
- **No Synthetic Imputation:** Partial-missing records (e.g. valid PM2.5 but offline NO2) are strictly preserved as `NaN` without synthetic mean/median imputation.
- **Hardware Fault Observation:** Siddharth Nagar-Worli's SO2 sensor suffered a persistent hardware outage resulting in 100.0% missing data (0 valid readings across 22 months).

**Outlier Diagnostics:**
- Outliers are identified per station using Tukey's Interquartile Range method: $[Q1 - 1.5 \times IQR, \quad Q3 + 1.5 \times IQR]$.
- Total PM2.5 readings flagged: 1,281 readings (2.41% of valid PM2.5 observations).
- Outliers are **retained** in the analysis rather than silently deleted, because physical shocks (industrial venting, winter temperature inversions, Diwali fireworks) represent genuine environmental exposure events.


---

## 4. Reproducibility Controls (added)

| Control               | Requirement                                                             |
| --------------------- | ----------------------------------------------------------------------- |
| Pinned versions       | Record the commit hash of each GitHub mirror used                       |
| Raw data immutability | Store raw downloads unmodified under `data/raw/` with SHA-256 checksums |
| Row-count manifest    | Per source: rows downloaded, rows after QC, rows dropped per QC step    |
| Retrieval log         | Timestamp, URL, HTTP status for every request                           |
| Determinism           | Fixed random seeds. Document the Overpass query text                    |
| Fresh-clone test      | One command rebuilds the dataset with no keys, from the manifest        |

## 5. Risks and Limitations (added)

1. **Mirror dependency.** The primary data comes through third-party GitHub mirrors. If one is removed or stops updating, the pipeline breaks. Mitigation: cache raw data, document the original CPCB source.
2. **Licence mixing.** CC BY-SA (bulletins) and ODbL (OSM) have share-alike terms. If derived data is redistributed, check compatibility before choosing an output licence.
3. **Open-Meteo commercial limits.** The free API is for non-commercial use. A commercial deployment needs a different arrangement.
4. **Station sparsity and gaps.** Monsoon months and sensor outages cause uneven coverage. Report coverage per station and year.
5. **Representativeness.** Reanalysis weather is gridded (~9–25 km), so it is smoother than street-level conditions.
6. **Freshness.** Historical archives lag real time. Do not describe this data as live.

## 6. Licence and Attribution

| Data                  | Licence                                                               | Required attribution                                                                                |
| --------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| CPCB air quality      | Government of India open data (GODL-India / NDSAP). Not public domain | Central Pollution Control Board (CPCB); Maharashtra Pollution Control Board (MPCB) where applicable |
| CPCB bulletins mirror | CC BY-SA 4.0 per repo **[verify]**                                    | Source: CPCB / MoEFCC, via `urbanemissionsinfo/AQI_bulletins`, CC BY-SA 4.0                         |
| Open-Meteo            | CC BY 4.0 (data), non-commercial (free API)                           | Weather data by Open-Meteo.com                                                                      |
| OpenStreetMap         | ODbL 1.0                                                              | © OpenStreetMap contributors                                                                        |

## 7. Data Integrity Statement

All tables, metrics and model validations are derived only from the sources in §2.1. No values are synthesised, imputed beyond the ≤ 2-hour interpolation in §3.1, or taken from undisclosed sources. Every figure in the report must be traceable to a raw file via the manifest in §4.

---
