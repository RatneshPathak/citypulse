"""
Download historical weather data from Open-Meteo Archive API for Mumbai.

Open-Meteo provides free, keyless access to historical weather data
under CC BY 4.0 license. Attribution: https://open-meteo.com/

This script downloads hourly weather data and caches it locally.

Usage:
    python -m src.ingest.weather_download
"""
import argparse
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

MUMBAI_LAT = 19.0760
MUMBAI_LON = 72.8777

MUMBAI_POINTS = {
    "mumbai_central": (19.0760, 72.8777),
    "mumbai_north": (19.2000, 72.8500),
    "mumbai_south": (18.9220, 72.8347),
    "navi_mumbai": (19.0330, 73.0297),
}

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
]

RAW_DIR = Path("data/raw/weather")
API_URL = "https://archive-api.open-meteo.com/v1/archive"

def download_weather_chunk(lat: float, lon: float,
                           start_date: str, end_date: str) -> pd.DataFrame:
    """Download one chunk of weather data from Open-Meteo."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "Asia/Kolkata",
    }

    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    if not hourly or "time" not in hourly:
        return pd.DataFrame()

    df = pd.DataFrame(hourly)
    df["latitude"] = data.get("latitude", lat)
    df["longitude"] = data.get("longitude", lon)
    return df

def download_weather(location_name: str, lat: float, lon: float,
                     start: str, end: str, chunk_months: int = 3) -> pd.DataFrame:
    """Download weather data in quarterly chunks with caching."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    all_frames = []

    current = start_dt
    while current < end_dt:
        chunk_end = min(
            current + timedelta(days=chunk_months * 30),
            end_dt
        )
        s_str = current.strftime("%Y-%m-%d")
        e_str = chunk_end.strftime("%Y-%m-%d")

        cache_file = RAW_DIR / f"{location_name}_{s_str}_{e_str}.csv"

        if cache_file.exists():
            print(f"  [CACHED] {location_name}: {s_str} to {e_str}")
            df = pd.read_csv(cache_file)
        else:
            print(f"  [DOWNLOAD] {location_name}: {s_str} to {e_str}")
            try:
                df = download_weather_chunk(lat, lon, s_str, e_str)
                if not df.empty:
                    df.to_csv(cache_file, index=False)
                time.sleep(1)
            except Exception as e:
                print(f"    Error: {e}")
                df = pd.DataFrame()

        if not df.empty:
            all_frames.append(df)

        current = chunk_end + timedelta(days=1)

    if all_frames:
        return pd.concat(all_frames, ignore_index=True)
    return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser(description="Download Open-Meteo weather data for Mumbai")
    parser.add_argument("--start", default="2023-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2026-09-30", help="End date YYYY-MM-DD")
    parser.add_argument("--location", default=None, help="Specific location key")
    args = parser.parse_args()

    locations = MUMBAI_POINTS
    if args.location:
        if args.location in MUMBAI_POINTS:
            locations = {args.location: MUMBAI_POINTS[args.location]}
        else:
            print(f"Unknown location: {args.location}. Available: {list(MUMBAI_POINTS.keys())}")
            return

    all_data = []
    for name, (lat, lon) in locations.items():
        print(f"\n--- Weather for {name} ({lat}, {lon}) ---")
        df = download_weather(name, lat, lon, args.start, args.end)
        if not df.empty:
            df["location_name"] = name
            all_data.append(df)
            print(f"  Got {len(df)} hourly records")

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        out_path = RAW_DIR / "open_meteo_mumbai.csv"
        combined.to_csv(out_path, index=False)
        print(f"\nSaved {len(combined)} total records to {out_path}")
        print(f"Date range: {combined['time'].min()} to {combined['time'].max()}")
    else:
        print("\nNo weather data downloaded!")

if __name__ == "__main__":
    main()
