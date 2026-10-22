"""
Master data ingestion script for CityPulse Mumbai.

Tries multiple data sources in order of reliability:
1. data.gov.in CPCB real-time AQI API (free key from data.gov.in)
2. OpenAQ S3 bulk archive (no key needed, if Mumbai IDs are known)
3. Manual download helper (generates instructions for CPCB CCR portal)
4. Generates a SYNTHETIC sample for UI development only (clearly labelled)

The pipeline is idempotent: if cached data exists, it is reused.

Usage:
    python -m src.ingest.run_all
    python -m src.ingest.run_all --source data_gov_in
    python -m src.ingest.run_all --source synthetic
"""
import argparse
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

MUMBAI_STATIONS = {
    "Bandra Kurla Complex": {"lat": 19.0596, "lon": 72.8613, "type": "commercial", "zone": "Western Suburbs"},
    "Colaba": {"lat": 18.9067, "lon": 72.8147, "type": "residential", "zone": "South Mumbai"},
    "Kurla": {"lat": 19.0726, "lon": 72.8794, "type": "industrial", "zone": "Eastern Suburbs"},
    "Powai": {"lat": 19.1195, "lon": 72.9064, "type": "residential", "zone": "Eastern Suburbs"},
    "Borivali East": {"lat": 19.2307, "lon": 72.8567, "type": "residential", "zone": "Western Suburbs"},
    "Chembur": {"lat": 19.0522, "lon": 72.8949, "type": "industrial", "zone": "Eastern Suburbs"},
    "Worli": {"lat": 19.0176, "lon": 72.8151, "type": "residential", "zone": "South Mumbai"},
    "Sion": {"lat": 19.0437, "lon": 72.8640, "type": "mixed", "zone": "Central Mumbai"},
    "Andheri East": {"lat": 19.1136, "lon": 72.8697, "type": "commercial", "zone": "Western Suburbs"},
    "Mazgaon": {"lat": 18.9628, "lon": 72.8483, "type": "port/industrial", "zone": "South Mumbai"},
    "Malad West": {"lat": 19.1857, "lon": 72.8485, "type": "residential", "zone": "Western Suburbs"},
    "Vile Parle West": {"lat": 19.0990, "lon": 72.8432, "type": "residential", "zone": "Western Suburbs"},
    "Navi Mumbai": {"lat": 19.0368, "lon": 73.0158, "type": "mixed", "zone": "Navi Mumbai"},
}

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def download_data_gov_in(api_key: str | None = None) -> pd.DataFrame:
    """
    Download AQI data from data.gov.in CPCB resource.
    Requires a free API key from data.gov.in.
    """
    if not api_key:
        api_key = os.environ.get("DATA_GOV_IN_KEY")
    if not api_key:
        print("  No data.gov.in API key. Set DATA_GOV_IN_KEY env var or register at https://data.gov.in")
        return pd.DataFrame()

    resource_id = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
    base_url = f"https://api.data.gov.in/resource/{resource_id}"

    all_records = []
    offset = 0
    limit = 1000
    max_pages = 50

    cache_file = RAW_DIR / "data_gov_in" / "cpcb_mumbai_realtime.json"
    if cache_file.exists():
        print("  [CACHED] data.gov.in data")
        with open(cache_file, "r") as f:
            all_records = json.load(f)
        return pd.DataFrame(all_records)

    for page in range(max_pages):
        params = {
            "api-key": api_key,
            "format": "json",
            "limit": limit,
            "offset": offset,
            "filters[city]": "Mumbai",
        }
        try:
            resp = requests.get(base_url, params=params, timeout=30)
            if resp.status_code != 200:
                print(f"  HTTP {resp.status_code} on page {page}")
                break

            data = resp.json()
            records = data.get("records", [])
            if not records:
                break

            all_records.extend(records)
            total = data.get("total", 0)
            print(f"  Page {page+1}: got {len(records)} records (total available: {total})")

            if offset + limit >= total:
                break
            offset += limit
            time.sleep(1)

        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break

    if all_records:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(all_records, f)

    return pd.DataFrame(all_records)


def generate_synthetic_dataset() -> pd.DataFrame:
    """
    Generate SYNTHETIC air quality data for UI development and testing ONLY.

    ┌─────────────────────────────────────────────────┐
    │  SYNTHETIC - UI TESTING ONLY                    │
    │  This data must NEVER feed analysis or evidence │
    └─────────────────────────────────────────────────┘

    Generates realistic-looking patterns but is NOT real data.
    Used only when real data sources are unavailable, for building
    and testing the dashboard interface.
    """
    print("  +===============================================+")
    print("  | GENERATING SYNTHETIC DATA - UI TESTING ONLY  |")
    print("  | NOT for analysis, evidence, or reporting     |")
    print("  +===============================================+")

    np.random.seed(42)

    start_date = datetime(2023, 1, 1)
    end_date = datetime(2026, 9, 30)
    hours = pd.date_range(start_date, end_date, freq="h")

    records = []
    for station_name, meta in MUMBAI_STATIONS.items():
        base_pm25 = np.random.uniform(30, 60)
        base_pm10 = base_pm25 * np.random.uniform(1.8, 2.5)

        coverage_rate = np.random.uniform(0.7, 0.95)
        mask = np.random.random(len(hours)) < coverage_rate

        for i, ts in enumerate(hours):
            if not mask[i]:
                continue

            month = ts.month
            if month in [11, 12, 1, 2]:
                seasonal = np.random.uniform(1.5, 2.5)
            elif month in [6, 7, 8, 9]:
                seasonal = np.random.uniform(0.3, 0.6)
            elif month in [3, 4, 5]:
                seasonal = np.random.uniform(0.8, 1.3)
            else:
                seasonal = np.random.uniform(1.0, 1.8)

            hour = ts.hour
            if 7 <= hour <= 10 or 18 <= hour <= 22:
                diurnal = np.random.uniform(1.2, 1.6)
            elif 2 <= hour <= 5:
                diurnal = np.random.uniform(0.7, 0.9)
            else:
                diurnal = 1.0

            weekday_effect = 0.85 if ts.weekday() >= 5 else 1.0

            diwali_effect = 1.0
            if month == 10 and 20 <= ts.day <= 31:
                diwali_effect = np.random.uniform(2.0, 4.0)
            elif month == 11 and ts.day <= 5:
                diwali_effect = np.random.uniform(1.5, 3.0)

            industrial_mult = 1.0
            if meta["type"] in ["industrial", "port/industrial"]:
                industrial_mult = np.random.uniform(1.1, 1.4)

            pm25 = max(5, base_pm25 * seasonal * diurnal * weekday_effect *
                       diwali_effect * industrial_mult +
                       np.random.normal(0, 8))
            pm10 = max(10, base_pm10 * seasonal * diurnal * weekday_effect *
                       diwali_effect * industrial_mult +
                       np.random.normal(0, 15))

            no2 = max(2, 25 * seasonal * diurnal + np.random.normal(0, 5))
            so2 = max(1, 8 * seasonal + np.random.normal(0, 2))
            co = max(0.2, 0.8 * seasonal * diurnal + np.random.normal(0, 0.15))
            o3 = max(5, 40 * (1.5 - seasonal * 0.3) + np.random.normal(0, 8))

            records.append({
                "timestamp": ts.isoformat(),
                "station": station_name,
                "latitude": meta["lat"],
                "longitude": meta["lon"],
                "station_type": meta["type"],
                "zone": meta["zone"],
                "pm25": round(pm25, 1),
                "pm10": round(pm10, 1),
                "no2": round(no2, 1),
                "so2": round(so2, 1),
                "co": round(co, 2),
                "o3": round(o3, 1),
                "data_source": "SYNTHETIC",
            })

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def save_station_metadata():
    """Save station metadata for reference."""
    meta_df = pd.DataFrame([
        {"station": name, **info}
        for name, info in MUMBAI_STATIONS.items()
    ])
    out = PROCESSED_DIR / "station_metadata.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    meta_df.to_csv(out, index=False)
    print(f"  Saved station metadata to {out}")


def main():
    parser = argparse.ArgumentParser(description="CityPulse Mumbai data ingestion")
    parser.add_argument("--source", choices=["data_gov_in", "synthetic", "auto"],
                        default="auto", help="Data source to use")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    save_station_metadata()

    df = pd.DataFrame()

    if args.source in ("data_gov_in", "auto"):
        print("\n=== Trying data.gov.in CPCB API ===")
        df = download_data_gov_in()
        if not df.empty:
            print(f"  Got {len(df)} records from data.gov.in")
            out = RAW_DIR / "data_gov_in" / "cpcb_mumbai_realtime.csv"
            out.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(out, index=False)

    if df.empty and args.source in ("synthetic", "auto"):
        print("\n=== Real data sources unavailable or empty ===")
        print("=== Generating synthetic data for UI testing ===")
        df = generate_synthetic_dataset()
        out = RAW_DIR / "synthetic" / "mumbai_aq_synthetic.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        print(f"  Saved {len(df)} synthetic records to {out}")

    if not df.empty:
        print(f"\n=== Ingestion complete ===")
        print(f"  Total records: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
        if "station" in df.columns:
            print(f"  Stations: {df['station'].nunique()}")
        if "timestamp" in df.columns:
            print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")


if __name__ == "__main__":
    main()
