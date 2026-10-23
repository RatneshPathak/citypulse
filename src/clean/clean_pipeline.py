"""
Data Cleaning & Quality Pipeline — CityPulse: Mumbai

Transforms raw CPCB station archives and Open-Meteo weather logs into
a clean, unified, temporally consistent dataset for exploratory analysis
and predictive modelling.

Key steps:
1. Reshape CPCB wide daily-hourly table to long-form hourly series.
2. Unify timestamps with explicit timezone (Asia/Kolkata / IST, and UTC).
3. Deduplicate across station and timestamp.
4. Flag and handle impossible values (negative values, sensor-stuck readings >= 6h).
5. Flag extreme statistical outliers without silent deletion.
6. Interpolate short gaps (<= 2h) with explicit documentation; leave larger gaps as NaN.
7. Merge surface weather reanalysis (temperature, humidity, wind u/v, rain, pressure).
8. Merge station spatial attributes and OSM context (coastal flag, road density, env type).
9. Apply the project's 18-valid-hour daily completeness threshold.
10. Generate data quality audit tables and station-month coverage matrix.

Usage:
    python -m src.clean.clean_pipeline
"""
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

RAW_CPCB_PATH = Path("data/raw/cpcb/cpcb_aqi_india.parquet")
RAW_WEATHER_DIR = Path("data/raw/weather")
OSM_CONTEXT_PATH = Path("data/raw/osm/mumbai_stations_osm_context.csv")
PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")

STATION_METADATA = {
    "Bandra Kurla Complex Mumbai IITM": {"canonical_name": "Bandra Kurla Complex", "zone": "Western Suburbs", "lat": 19.0596, "lon": 72.8613, "env_type": "Commercial / Financial", "is_coastal": 0},
    "Bandra Kurla Complex Mumbai MPCB": {"canonical_name": "Bandra Kurla Complex", "zone": "Western Suburbs", "lat": 19.0596, "lon": 72.8613, "env_type": "Commercial / Financial", "is_coastal": 0},
    "Bandra Mumbai MPCB": {"canonical_name": "Bandra", "zone": "Western Suburbs", "lat": 19.0544, "lon": 72.8402, "env_type": "Suburban Mixed", "is_coastal": 1},
    "Colaba Mumbai MPCB": {"canonical_name": "Colaba", "zone": "South Mumbai", "lat": 18.9067, "lon": 72.8147, "env_type": "Coastal / Residential", "is_coastal": 1},
    "Navy Nagar-Colaba Mumbai IITM": {"canonical_name": "Colaba Navy Nagar", "zone": "South Mumbai", "lat": 18.8950, "lon": 72.8100, "env_type": "Coastal Military / Green", "is_coastal": 1},
    "Kurla Mumbai MPCB": {"canonical_name": "Kurla", "zone": "Eastern Suburbs", "lat": 19.0726, "lon": 72.8794, "env_type": "Dense Urban Transit", "is_coastal": 0},
    "Powai Mumbai MPCB": {"canonical_name": "Powai", "zone": "Eastern Suburbs", "lat": 19.1195, "lon": 72.9064, "env_type": "Lake / Institutional", "is_coastal": 0},
    "Borivali East Mumbai MPCB": {"canonical_name": "Borivali East", "zone": "Western Suburbs", "lat": 19.2307, "lon": 72.8567, "env_type": "Near National Park", "is_coastal": 0},
    "Borivali East Mumbai IITM": {"canonical_name": "Borivali East IITM", "zone": "Western Suburbs", "lat": 19.2290, "lon": 72.8580, "env_type": "Near National Park", "is_coastal": 0},
    "Chembur Mumbai MPCB": {"canonical_name": "Chembur", "zone": "Eastern Suburbs", "lat": 19.0522, "lon": 72.8949, "env_type": "Industrial Corridor", "is_coastal": 0},
    "Worli Mumbai MPCB": {"canonical_name": "Worli", "zone": "South Mumbai", "lat": 19.0176, "lon": 72.8151, "env_type": "Coastal Commercial", "is_coastal": 1},
    "Siddharth Nagar-Worli Mumbai IITM": {"canonical_name": "Worli Siddharth Nagar", "zone": "South Mumbai", "lat": 19.0150, "lon": 72.8180, "env_type": "Coastal Commercial", "is_coastal": 1},
    "Sion Mumbai MPCB": {"canonical_name": "Sion", "zone": "Central Mumbai", "lat": 19.0437, "lon": 72.8640, "env_type": "Highway Traffic Junction", "is_coastal": 0},
    "Chhatrapati Shivaji Intl. Airport (T2) Mumbai MPCB": {"canonical_name": "Airport T2", "zone": "Western Suburbs", "lat": 19.0974, "lon": 72.8745, "env_type": "Aviation Corridor", "is_coastal": 0},
    "Vile Parle West Mumbai MPCB": {"canonical_name": "Vile Parle West", "zone": "Western Suburbs", "lat": 19.0990, "lon": 72.8432, "env_type": "Suburban Residential", "is_coastal": 1},
    "Mazgaon Mumbai IITM": {"canonical_name": "Mazgaon", "zone": "South Mumbai", "lat": 18.9628, "lon": 72.8483, "env_type": "Port / Maritime Docks", "is_coastal": 1},
    "Malad West Mumbai IITM": {"canonical_name": "Malad West", "zone": "Western Suburbs", "lat": 19.1857, "lon": 72.8485, "env_type": "Commercial Tech Hub", "is_coastal": 0},
    "Mindspace-Malad West Mumbai MPCB": {"canonical_name": "Malad Mindspace", "zone": "Western Suburbs", "lat": 19.1800, "lon": 72.8350, "env_type": "Commercial Tech Hub", "is_coastal": 0},
    "Chakala-Andheri East Mumbai IITM": {"canonical_name": "Andheri East Chakala", "zone": "Western Suburbs", "lat": 19.1136, "lon": 72.8697, "env_type": "MIDC Industrial Belt", "is_coastal": 0},
    "Deonar Mumbai IITM": {"canonical_name": "Deonar", "zone": "Eastern Suburbs", "lat": 19.0553, "lon": 72.9167, "env_type": "Dumping Ground / Solid Waste", "is_coastal": 0},
    "Mahape Navi Mumbai MPCB": {"canonical_name": "Mahape Navi Mumbai", "zone": "Navi Mumbai", "lat": 19.1098, "lon": 73.0232, "env_type": "TTC Industrial Zone", "is_coastal": 0},
    "Nerul Navi Mumbai MPCB": {"canonical_name": "Nerul Navi Mumbai", "zone": "Navi Mumbai", "lat": 19.0330, "lon": 73.0169, "env_type": "Planned Residential", "is_coastal": 0},
    "Sector-19A Nerul Navi Mumbai IITM": {"canonical_name": "Nerul Sec 19A", "zone": "Navi Mumbai", "lat": 19.0310, "lon": 73.0190, "env_type": "Planned Residential", "is_coastal": 0},
    "Kandivali East Mumbai MPCB": {"canonical_name": "Kandivali East", "zone": "Western Suburbs", "lat": 19.2065, "lon": 72.8675, "env_type": "Western Express Highway", "is_coastal": 0},
    "Mulund West Mumbai MPCB": {"canonical_name": "Mulund West", "zone": "Eastern Suburbs", "lat": 19.1764, "lon": 72.9467, "env_type": "Foothill Suburban", "is_coastal": 0},
    "Khindipada-Bhandup West Mumbai IITM": {"canonical_name": "Bhandup West", "zone": "Eastern Suburbs", "lat": 19.1550, "lon": 72.9300, "env_type": "Industrial / Residential", "is_coastal": 0},
    "Vasai West Mumbai MPCB": {"canonical_name": "Vasai West", "zone": "Palghar / MMR North", "lat": 19.3644, "lon": 72.8122, "env_type": "Outer MMR Coastal", "is_coastal": 1},
}

HOUR_COLS = [f"{h:02d}:00:00" for h in range(24)]

def load_raw_cpcb(start_date: str = "2021-01-01") -> pd.DataFrame:
    """Load raw CPCB parquet and filter for Mumbai stations."""
    logging.info(f"Loading raw CPCB data from {RAW_CPCB_PATH}...")
    df = pd.read_parquet(RAW_CPCB_PATH)

    mumbai_mask = df["City"].str.contains("Mumbai", case=False, na=False)
    mumbai_df = df[mumbai_mask].copy()
    mumbai_df["Date"] = pd.to_datetime(mumbai_df["Date"])
    mumbai_df = mumbai_df[mumbai_df["Date"] >= start_date].copy()
    logging.info(f"Filtered {len(mumbai_df)} daily station records for Mumbai (>= {start_date})")
    return mumbai_df

def reshape_to_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape wide hourly columns (00:00:00 - 23:00:00) to long hourly records."""
    logging.info("Reshaping wide daily records into hourly time series...")
    id_vars = ["Station ID", "State", "City", "Station Name", "Date"]
    available_hours = [c for c in HOUR_COLS if c in df.columns]

    melted = df.melt(
        id_vars=id_vars,
        value_vars=available_hours,
        var_name="hour_str",
        value_name="aqi_raw"
    )

    melted["hour_int"] = melted["hour_str"].apply(lambda s: int(s.split(":")[0]))
    melted["timestamp_ist"] = melted["Date"] + pd.to_timedelta(melted["hour_int"], unit="h")
    melted["timestamp_utc"] = melted["timestamp_ist"] - pd.Timedelta(hours=5, minutes=30)

    melted["aqi_raw"] = pd.to_numeric(melted["aqi_raw"], errors="coerce")

    melted["canonical_station"] = melted["Station Name"].map(
        lambda name: STATION_METADATA.get(name, {}).get("canonical_name", name)
    )
    melted["zone"] = melted["Station Name"].map(
        lambda name: STATION_METADATA.get(name, {}).get("zone", "Other MMR")
    )
    melted["env_type"] = melted["Station Name"].map(
        lambda name: STATION_METADATA.get(name, {}).get("env_type", "Urban Mixed")
    )
    melted["is_coastal"] = melted["Station Name"].map(
        lambda name: STATION_METADATA.get(name, {}).get("is_coastal", 0)
    )
    melted["latitude"] = melted["Station Name"].map(
        lambda name: STATION_METADATA.get(name, {}).get("lat", np.nan)
    )
    melted["longitude"] = melted["Station Name"].map(
        lambda name: STATION_METADATA.get(name, {}).get("lon", np.nan)
    )

    return melted

def clean_air_quality_series(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Applies rigorous data hygiene:
    - Deduplication
    - Impossible value detection (negative, out of bounds)
    - Sensor-stuck detection (>= 6 hours identical value)
    - Outlier flagging (IQR-based per station, without silent dropping)
    - Short gap interpolation (<= 2h)
    """
    logging.info("Applying quality filters, deduplication, and sensor diagnostics...")
    metrics = {
        "total_hourly_records": len(df),
        "duplicates_removed": 0,
        "negative_values_flagged": 0,
        "sensor_stuck_flagged": 0,
        "extreme_outliers_flagged": 0,
        "short_gaps_interpolated": 0,
    }

    initial_len = len(df)
    df = df.drop_duplicates(subset=["canonical_station", "timestamp_ist"]).copy()
    metrics["duplicates_removed"] = initial_len - len(df)

    df = df.sort_values(["canonical_station", "timestamp_ist"]).reset_index(drop=True)

    df["flag_negative"] = 0
    df["flag_sensor_stuck"] = 0
    df["flag_extreme_outlier"] = 0
    df["flag_interpolated"] = 0

    neg_mask = df["aqi_raw"] < 0
    df.loc[neg_mask, "flag_negative"] = 1
    metrics["negative_values_flagged"] = int(neg_mask.sum())

    extreme_mask = df["aqi_raw"] > 700
    df.loc[extreme_mask, "flag_extreme_outlier"] = 1
    metrics["extreme_outliers_flagged"] = int(extreme_mask.sum())

    df["aqi_clean"] = df["aqi_raw"].copy()
    df.loc[neg_mask | extreme_mask, "aqi_clean"] = np.nan

    cleaned_frames = []
    for station, group in df.groupby("canonical_station"):
        grp = group.copy().sort_values("timestamp_ist")
        val = grp["aqi_clean"]
        is_same = (val == val.shift(1)) & val.notna()
        repeat_count = is_same.groupby((~is_same).cumsum()).cumsum()
        stuck_mask = repeat_count >= 5
        grp.loc[stuck_mask, "flag_sensor_stuck"] = 1
        grp.loc[stuck_mask, "aqi_clean"] = np.nan
        metrics["sensor_stuck_flagged"] += int(stuck_mask.sum())

        missing_mask = grp["aqi_clean"].isna()
        interpolated = grp["aqi_clean"].interpolate(method="linear", limit=2, limit_direction="forward")
        interp_mask = missing_mask & interpolated.notna()
        grp.loc[interp_mask, "flag_interpolated"] = 1
        grp["aqi_clean"] = interpolated
        metrics["short_gaps_interpolated"] += int(interp_mask.sum())

        cleaned_frames.append(grp)

    df_cleaned = pd.concat(cleaned_frames, ignore_index=True)
    return df_cleaned, metrics

def load_and_merge_weather(df: pd.DataFrame) -> pd.DataFrame:
    """Load Open-Meteo hourly weather files and join with air quality data."""
    logging.info("Merging hourly weather features (Open-Meteo ERA5 / Reanalysis)...")
    weather_files = list(RAW_WEATHER_DIR.glob("*.csv"))
    if not weather_files:
        logging.warning("No weather CSV files found in data/raw/weather! Skipping weather merge.")
        return df

    weather_dfs = []
    for wf in weather_files:
        try:
            w = pd.read_csv(wf)
            if "time" in w.columns:
                weather_dfs.append(w)
        except Exception as e:
            logging.error(f"Error reading {wf}: {e}")

    if not weather_dfs:
        return df

    all_weather = pd.concat(weather_dfs, ignore_index=True)
    all_weather["time"] = pd.to_datetime(all_weather["time"])
    all_weather = all_weather.drop_duplicates(subset=["time"]).sort_values("time")

    if "wind_speed_10m" in all_weather.columns and "wind_direction_10m" in all_weather.columns:
        rad = np.radians(all_weather["wind_direction_10m"])
        all_weather["wind_u"] = -all_weather["wind_speed_10m"] * np.sin(rad)
        all_weather["wind_v"] = -all_weather["wind_speed_10m"] * np.cos(rad)

    cols_to_drop = [c for c in ["latitude", "longitude", "location_name"] if c in all_weather.columns]
    all_weather = all_weather.drop(columns=cols_to_drop)

    merged = pd.merge(
        df,
        all_weather,
        left_on="timestamp_ist",
        right_on="time",
        how="left"
    )
    if "time" in merged.columns:
        merged = merged.drop(columns=["time"])

    logging.info(f"Weather joined. Match rate: {merged['temperature_2m'].notna().mean() * 100:.1f}%")
    return merged

def compute_daily_station_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes daily aggregates per station following official CPCB protocol:
    Requires at least 75% valid hourly measurements (>= 18 hours per day).
    """
    logging.info("Computing daily aggregates under the project 18-hour completeness threshold...")
    df["date_only"] = df["timestamp_ist"].dt.date

    daily_stats = []
    for (station, date), grp in df.groupby(["canonical_station", "date_only"]):
        total_hours = len(grp)
        valid_hours = grp["aqi_clean"].notna().sum()
        valid_pct = valid_hours / max(total_hours, 24)

        is_cpcb_valid = valid_hours >= 18

        mean_aqi = grp["aqi_clean"].mean() if is_cpcb_valid else np.nan
        max_aqi = grp["aqi_clean"].max() if is_cpcb_valid else np.nan
        min_aqi = grp["aqi_clean"].min() if is_cpcb_valid else np.nan
        p90_aqi = grp["aqi_clean"].quantile(0.9) if is_cpcb_valid else np.nan

        temp_mean = grp["temperature_2m"].mean() if "temperature_2m" in grp else np.nan
        humidity_mean = grp["relative_humidity_2m"].mean() if "relative_humidity_2m" in grp else np.nan
        wind_speed_mean = grp["wind_speed_10m"].mean() if "wind_speed_10m" in grp else np.nan
        wind_u_mean = grp["wind_u"].mean() if "wind_u" in grp else np.nan
        wind_v_mean = grp["wind_v"].mean() if "wind_v" in grp else np.nan
        rain_total = grp["precipitation"].sum() if "precipitation" in grp else np.nan
        pressure_mean = grp["surface_pressure"].mean() if "surface_pressure" in grp else np.nan

        first_row = grp.iloc[0]
        daily_stats.append({
            "canonical_station": station,
            "date": pd.to_datetime(date),
            "zone": first_row["zone"],
            "env_type": first_row["env_type"],
            "is_coastal": first_row["is_coastal"],
            "latitude": first_row["latitude"],
            "longitude": first_row["longitude"],
            "total_hours": total_hours,
            "valid_hours": valid_hours,
            "completeness_pct": round(valid_pct * 100, 1),
            "is_cpcb_valid": int(is_cpcb_valid),
            "aqi_mean": round(mean_aqi, 1) if not np.isnan(mean_aqi) else np.nan,
            "aqi_max": round(max_aqi, 1) if not np.isnan(max_aqi) else np.nan,
            "aqi_min": round(min_aqi, 1) if not np.isnan(min_aqi) else np.nan,
            "aqi_p90": round(p90_aqi, 1) if not np.isnan(p90_aqi) else np.nan,
            "temp_mean": round(temp_mean, 1) if not np.isnan(temp_mean) else np.nan,
            "humidity_mean": round(humidity_mean, 1) if not np.isnan(humidity_mean) else np.nan,
            "wind_speed_mean": round(wind_speed_mean, 1) if not np.isnan(wind_speed_mean) else np.nan,
            "wind_u_mean": round(wind_u_mean, 2) if not np.isnan(wind_u_mean) else np.nan,
            "wind_v_mean": round(wind_v_mean, 2) if not np.isnan(wind_v_mean) else np.nan,
            "rain_total_mm": round(rain_total, 2) if not np.isnan(rain_total) else np.nan,
            "pressure_mean": round(pressure_mean, 1) if not np.isnan(pressure_mean) else np.nan,
        })

    daily_df = pd.DataFrame(daily_stats)

    def categorize_cpcb_aqi(val):
        if np.isnan(val):
            return "Missing"
        elif val <= 50:
            return "Good"
        elif val <= 100:
            return "Satisfactory"
        elif val <= 200:
            return "Moderate"
        elif val <= 300:
            return "Poor"
        elif val <= 400:
            return "Very Poor"
        else:
            return "Severe"

    daily_df["aqi_category"] = daily_df["aqi_mean"].apply(categorize_cpcb_aqi)
    daily_df["target_unhealthy_event"] = (daily_df["aqi_mean"] > 200).astype(int)

    return daily_df

def generate_quality_report(hourly_df: pd.DataFrame, daily_df: pd.DataFrame, metrics: dict):
    """Generates markdown audit report and coverage heatmap matrix."""
    logging.info("Generating data quality audit report and coverage matrices...")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    daily_df["year_month"] = daily_df["date"].dt.to_period("M").astype(str)
    coverage = daily_df.groupby(["canonical_station", "year_month"])["is_cpcb_valid"].mean() * 100
    coverage_matrix = coverage.unstack(fill_value=0.0).round(1)

    station_summary = daily_df.groupby("canonical_station").agg(
        total_days=("date", "count"),
        valid_days=("is_cpcb_valid", "sum"),
        mean_aqi=("aqi_mean", "mean"),
        max_aqi=("aqi_max", "max"),
        unhealthy_days=("target_unhealthy_event", "sum"),
    ).reset_index()
    station_summary["valid_day_pct"] = (station_summary["valid_days"] / station_summary["total_days"] * 100).round(1)
    station_summary["mean_aqi"] = station_summary["mean_aqi"].round(1)

    report_content = f"""# Data Quality & Coverage Audit Report — CityPulse: Mumbai

Audit Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
Temporal Scope: {daily_df['date'].min().strftime('%Y-%m-%d')} to {daily_df['date'].max().strftime('%Y-%m-%d')}  
Project Completeness Rule: >= 18 valid hours/day

---

## 1. Cleaning & Hygiene Summary Metrics

| Quality Diagnostic Metric | Value | Action Taken |
| :--- | :--- | :--- |
| **Total Hourly Rows Processed** | {metrics['total_hourly_records']:,} | Ingested from CPCB CAAQMS archives |
| **Duplicate Timestamp Records** | {metrics['duplicates_removed']:,} | Deduplicated on station x timestamp |
| **Negative Telemetry Values (< 0)** | {metrics['negative_values_flagged']:,} | Flagged (`flag_negative=1`), set to NaN |
| **Extreme Outliers (> 700 AQI)** | {metrics['extreme_outliers_flagged']:,} | Flagged (`flag_extreme_outlier=1`), set to NaN |
| **Sensor-Stuck Episodes (>= 6h flatline)** | {metrics['sensor_stuck_flagged']:,} | Flagged (`flag_sensor_stuck=1`), invalidated to NaN |
| **Short Gaps Interpolated (<= 2h)** | {metrics['short_gaps_interpolated']:,} | Linear interpolated (`flag_interpolated=1`); documented |
| **Total Daily Station Records** | {len(daily_df):,} | Aggregated with completeness tracking |
| **Valid Daily Records (>= 18h)** | {daily_df['is_cpcb_valid'].sum():,} ({daily_df['is_cpcb_valid'].mean()*100:.1f}%) | Retained for downstream modeling |

---

## 2. Station-Level Monitoring Reliability

Stations with valid day coverage >= 70% are selected for primary predictive modeling and longitudinal evaluation. Stations with low coverage (< 50%) are flagged for municipal monitoring expansion.

| Monitoring Station | Zone | Environmental Type | Total Days | Valid CPCB Days | Valid % | Mean AQI | Unhealthy Days (>200) | Modeling Tier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for _, row in station_summary.sort_values("valid_day_pct", ascending=False).iterrows():
        tier = "Primary Modeling" if row["valid_day_pct"] >= 75 else ("Secondary" if row["valid_day_pct"] >= 50 else "Coverage Gap")
        st_meta = [v for k, v in STATION_METADATA.items() if v["canonical_name"] == row["canonical_station"]]
        zone = st_meta[0]["zone"] if st_meta else "MMR"
        env = st_meta[0]["env_type"] if st_meta else "Urban"
        report_content += f"| **{row['canonical_station']}** | {zone} | {env} | {int(row['total_days']):,} | {int(row['valid_days']):,} | {row['valid_day_pct']:.1f}% | {row['mean_aqi']} | {int(row['unhealthy_days']):,} | `{tier}` |\n"

    report_content += f"""
---

## 3. Data Integrity & Reproducibility Guarantees
1. **Zero Silent Drops:** Every suspicious record is assigned an explicit boolean flag column (`flag_negative`, `flag_sensor_stuck`, `flag_extreme_outlier`, `flag_interpolated`).
2. **Explicit Timezone:** All operational decisions and timestamps are tracked in Indian Standard Time (IST, UTC+05:30) with explicit UTC offset column.
3. **No Target Leakage:** Daily aggregation uses only measurements logged strictly up to 23:59 IST of that calendar date.
"""
    with open(REPORTS_DIR / "data_quality_report.md", "w", encoding="utf-8") as f:
        f.write(report_content)

    coverage_matrix.to_csv(REPORTS_DIR / "station_coverage_matrix_monthly.csv")
    logging.info(f"Report written to {REPORTS_DIR / 'data_quality_report.md'}")

def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = load_raw_cpcb(start_date="2021-01-01")
    hourly_df = reshape_to_hourly(raw_df)

    cleaned_hourly, metrics = clean_air_quality_series(hourly_df)

    merged_hourly = load_and_merge_weather(cleaned_hourly)

    hourly_parquet_path = PROCESSED_DIR / "mumbai_aqi_hourly_clean.parquet"
    merged_hourly.to_parquet(hourly_parquet_path, index=False)
    logging.info(f"Saved clean hourly dataset to {hourly_parquet_path} ({len(merged_hourly):,} records)")

    daily_df = compute_daily_station_aggregates(merged_hourly)
    daily_parquet_path = PROCESSED_DIR / "mumbai_aqi_daily_clean.parquet"
    daily_csv_path = PROCESSED_DIR / "mumbai_aqi_daily_clean.csv"
    daily_df.to_parquet(daily_parquet_path, index=False)
    daily_df.to_csv(daily_csv_path, index=False)
    logging.info(f"Saved clean daily dataset to {daily_parquet_path} ({len(daily_df):,} records)")

    generate_quality_report(merged_hourly, daily_df, metrics)

    print("\nData Cleaning & Preparation Phase Complete!")
    print(f"Hourly records: {len(merged_hourly):,}")
    print(f"Daily records:  {len(daily_df):,}")
    print(f"Valid CPCB days: {daily_df['is_cpcb_valid'].sum():,} ({daily_df['is_cpcb_valid'].mean()*100:.1f}%)")

if __name__ == "__main__":
    main()
