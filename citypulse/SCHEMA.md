# Data Schema Documentation — CityPulse: Mumbai

Location: `/data/processed/`  
Format: Apache Parquet (`.parquet`) and CSV (`.csv`)  
Timezone: Explicitly documented as Indian Standard Time (`Asia/Kolkata` / UTC+05:30) and UTC.

---

## 1. Hourly Clean Dataset (`mumbai_aqi_hourly_clean.parquet`)

One row per station per hour.

| Field Name | Type | Unit / Format | Description |
| :--- | :--- | :--- | :--- |
| `Station ID` | String | e.g. `site_5964` | CPCB official monitoring site identifier |
| `Station Name` | String | e.g. `Sion Mumbai MPCB` | Full raw station name from regulatory agency |
| `canonical_station` | String | e.g. `Sion`, `Bandra Kurla Complex` | Cleaned standardized station name |
| `zone` | String | Category | Mumbai sub-region (`South Mumbai`, `Western Suburbs`, `Eastern Suburbs`, `Central Mumbai`, `Navi Mumbai`) |
| `env_type` | String | Category | Station micro-environment (e.g. `Highway Traffic Junction`, `Commercial / Financial`, `Coastal / Residential`) |
| `is_coastal` | Integer | `0` or `1` | Binary flag indicating Arabian Sea coastal proximity (< 2 km) |
| `latitude` | Float | Decimal degrees | Station latitude coordinate |
| `longitude` | Float | Decimal degrees | Station longitude coordinate |
| `timestamp_ist` | Datetime | `YYYY-MM-DD HH:MM:SS` | Timestamp in Indian Standard Time (IST, UTC+05:30) |
| `timestamp_utc` | Datetime | `YYYY-MM-DD HH:MM:SS` | Timestamp normalized to UTC |
| `aqi_raw` | Float | 0 – 500+ | Raw continuous air quality index measurement as transmitted by station |
| `aqi_clean` | Float | 0 – 500+ | Cleaned measurement with invalid readings set to NaN and short gaps (<=2h) interpolated |
| `flag_negative` | Integer | `0` or `1` | 1 if raw telemetry reported impossible negative concentration |
| `flag_sensor_stuck` | Integer | `0` or `1` | 1 if sensor flatlined with identical non-null value for >= 6 consecutive hours |
| `flag_extreme_outlier`| Integer | `0` or `1` | 1 if raw measurement exceeded plausible physical threshold (> 700) |
| `flag_interpolated` | Integer | `0` or `1` | 1 if value was imputed via linear interpolation across short gap (<= 2h) |
| `temperature_2m` | Float | °C | Surface air temperature at 2 meters (Open-Meteo ERA5 / Reanalysis) |
| `relative_humidity_2m`| Float | % | Relative humidity at 2 meters |
| `dew_point_2m` | Float | °C | Dew point temperature |
| `precipitation` | Float | mm | Total liquid water precipitation during the hour |
| `surface_pressure` | Float | hPa | Atmospheric pressure at station elevation |
| `wind_speed_10m` | Float | km/h | Horizontal wind speed at 10 meters elevation |
| `wind_direction_10m`| Float | Degrees (0-360) | Wind direction from which wind originates |
| `wind_u` | Float | km/h | Zonal wind component ($u = -ws \cdot \sin(\theta)$); positive = westerly (sea breeze in Mumbai) |
| `wind_v` | Float | km/h | Meridional wind component ($v = -ws \cdot \cos(\theta)$); positive = southerly |
| `shortwave_radiation`| Float | W/m² | Solar irradiance flux |

---

## 2. Daily Station Aggregates (`mumbai_aqi_daily_clean.parquet` / `.csv`)

One row per station per calendar day. Follows CPCB regulatory criteria (>= 75% completeness = >= 18 valid hours/day).

| Field Name | Type | Unit / Format | Description |
| :--- | :--- | :--- | :--- |
| `canonical_station` | String | e.g. `Bandra Kurla Complex` | Cleaned station identifier |
| `date` | Datetime | `YYYY-MM-DD` | Calendar date (IST) |
| `zone` | String | Category | Mumbai metropolitan zone |
| `env_type` | String | Category | Micro-environment classification |
| `is_coastal` | Integer | `0` or `1` | Proximity to coast flag |
| `latitude` | Float | Decimal degrees | Station latitude |
| `longitude` | Float | Decimal degrees | Station longitude |
| `total_hours` | Integer | 0 – 24 | Number of hourly observations logged |
| `valid_hours` | Integer | 0 – 24 | Number of verified valid hourly observations |
| `completeness_pct` | Float | 0.0 – 100.0% | Percentage of valid hours in the day |
| `is_cpcb_valid` | Integer | `0` or `1` | Binary flag indicating compliance with CPCB >= 75% rule (>= 18 valid hours) |
| `aqi_mean` | Float | 0 – 500 | 24-hour mean AQI (NaN if `is_cpcb_valid == 0`) |
| `aqi_max` | Float | 0 – 500 | Peak hourly AQI observed during the day |
| `aqi_min` | Float | 0 – 500 | Minimum hourly AQI observed |
| `aqi_p90` | Float | 0 – 500 | 90th percentile hourly AQI |
| `temp_mean` | Float | °C | 24-hour mean temperature |
| `humidity_mean` | Float | % | 24-hour mean relative humidity |
| `wind_speed_mean` | Float | km/h | 24-hour mean wind speed |
| `wind_u_mean` | Float | km/h | Mean zonal wind component (sea-breeze proxy) |
| `wind_v_mean` | Float | km/h | Mean meridional wind component |
| `rain_total_mm` | Float | mm | Daily cumulative rainfall |
| `pressure_mean` | Float | hPa | 24-hour mean surface atmospheric pressure |
| `aqi_category` | String | Category | Official Indian AQI class (`Good`, `Satisfactory`, `Moderate`, `Poor`, `Very Poor`, `Severe`) |
| `target_unhealthy_event`| Integer | `0` or `1` | Binary event indicator: 1 if `aqi_mean > 200` (Poor or worse), 0 otherwise |

---

## 3. CPCB Advance Search Cleaned Dataset (`citypulse_cleaned_data.csv` / `.parquet`)

Derived directly from `src/clean/aqi_cleaning.py` and `src/CityPulse_AQI_Cleaning_EDA.ipynb`.
One row per station per hour for the 4 core monitoring stations (2025-01-01 to 2026-10-22).

| Field Name | Type | Unit | Description |
| :--- | :--- | :--- | :--- |
| `From Date` | Datetime | `YYYY-MM-DD HH:MM:SS` (IST) | Beginning of 1-hour sampling interval |
| `To Date` | Datetime | `YYYY-MM-DD HH:MM:SS` (IST) | End of 1-hour sampling interval |
| `Station` | String | Categorical | Full station name (e.g. `Bandra Kurla Complex, Mumbai - IITM`) |
| `PM2.5` | Float | µg/m³ | Fine particulate matter (aerodynamic diameter ≤ 2.5 µm) |
| `PM10` | Float | µg/m³ | Coarse particulate matter (aerodynamic diameter ≤ 10 µm) |
| `NO` | Float | µg/m³ | Nitric oxide concentration |
| `NO2` | Float | µg/m³ | Nitrogen dioxide concentration |
| `NH3` | Float | µg/m³ | Ammonia concentration |
| `SO2` | Float | µg/m³ | Sulphur dioxide concentration (note: Worli is 100% NaN) |
| `CO` | Float | mg/m³ | Carbon monoxide concentration |

---

## 4. Station Multi-Pollutant Summary (`citypulse_station_summary.csv`)

Aggregated descriptive statistics across all 7 monitored pollutants for each continuous station.
Columns per pollutant: `mean`, `median`, `min`, `max`, `count`.

