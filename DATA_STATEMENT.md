# Data Statement — CityPulse: Mumbai

## Dataset 1: Continuous Ambient Air Quality Monitoring (CAAQMS)
- **Name:** CPCB CAAQMS India Continuous Station Archive & AQI Bulletins
- **Publisher:** Central Pollution Control Board (CPCB) & Maharashtra Pollution Control Board (MPCB), Government of India
- **Source URL:** https://app.cpcbccr.com / Open Government Data Platform India (data.gov.in) / Public CAAQMS mirrors (`Vonter/india-cpcb-aqi`, `urbanemissionsinfo/AQI_bulletins`)
- **Date Accessed:** October 2026
- **Licence / Terms:** Government Open Data (National Data Sharing and Accessibility Policy - NDSAP)
- **Access Method:** Bundled Parquet copy of a public CPCB data mirror; source mirror terms need independent verification before publication
- **Geographic Coverage:** Mumbai Metropolitan Region (Greater Mumbai, Navi Mumbai, Palghar corridor), India (Bounding Box: 18.85°N – 19.40°N, 72.75°E – 73.10°E)
- **Time Coverage:** Latest available multi-year continuous records (597,912 deduplicated hourly AQI rows across 36 station labels)
- **Fields Used:** `Station ID`, `Station Name`, `Date`, and hourly AQI columns (`00:00:00` – `23:00:00`). This file does not contain pollutant-specific concentration columns.
- **Known Gaps & Quality Issues:**
  - Sensor flatlines: 7,056 hourly records flagged where sensors repeated identical values for $\ge 6$ consecutive hours.
  - Siting bias: Monitors are predominantly positioned near ground-level arterial highway junctions or institutional complexes.

## Dataset 2: Historical Surface Meteorology
- **Name:** Open-Meteo Historical Weather Archive (ERA5 / Numerical Reanalysis)
- **Publisher:** Open-Meteo GmbH
- **Source URL:** https://archive-api.open-meteo.com/v1/archive
- **Date Accessed:** October 2026
- **Licence / Terms:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Access Method:** Public keyless REST API download
- **Geographic Coverage:** Mumbai Central Coordinates (19.0760°N, 72.8777°E)
- **Time Coverage:** Latest available multi-year continuous records (26,280 continuous hourly observations)
- **Fields Used:** `temperature_2m` (°C), `relative_humidity_2m` (%), `precipitation` (mm), `surface_pressure` (hPa), `wind_speed_10m` (km/h), `wind_direction_10m` (deg), `shortwave_radiation` (W/m²)
- **Known Gaps & Quality Issues:**
  - 0.25° spatial grid resolution smooths out micro-climatic coastal sea-breeze boundaries.

## Dataset 3: Urban Context & Infrastructure
- **Name:** OpenStreetMap Infrastructure & Land Use Extracts
- **Publisher:** OpenStreetMap Foundation
- **Source URL:** https://overpass-api.de
- **Date Accessed:** October 2026
- **Licence / Terms:** Open Database License 1.0 (ODbL) (© OpenStreetMap contributors)
- **Fields Used:** Major road segment density (`highway=primary|secondary|trunk`), industrial zones (`landuse=industrial`), parks (`leisure=park`), coastal proximity.

## Preprocessing & Data Hygiene
1. **Filtering:** Filtered strictly to monitoring stations within the Mumbai Metropolitan Region.
2. **Missing-Value Handling:** Short temporal gaps ($\le 2$ consecutive hours) linear interpolated and explicitly flagged (`flag_interpolated=1`). Days with fewer than 18 valid hours are excluded under this project's completeness rule.
3. **Duplicate Handling:** Deduplicated on `(canonical_station, timestamp_ist)`.
4. **Outlier Handling:** Sensor-stuck flatlines ($\ge 6$ identical hours) flagged (`flag_sensor_stuck=1`) and set to NaN. Extreme values ($> 700$ AQI) flagged without silent deletion.
5. **Joins:** Joined hourly meteorology on explicit Indian Standard Time (`Asia/Kolkata` / UTC+05:30) timestamps with 100% temporal alignment.
6. **Derived Features:** Zonal sea-breeze wind vector ($u$), meridional wind vector ($v$), atmospheric stagnation index, 7-day rolling statistics, and cyclical calendar transforms.

## Synthetic Data
- **Zero synthetic data used as evidence or for analytical conclusions.** All models, baselines, and exploratory findings are derived 100% from real public observations.

## Privacy
- No personal, private, or sensitive individual data is used, stored, or published.
