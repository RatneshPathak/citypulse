"""
Download hourly air-quality data from the CPCB CAAQMS public portal.

The CPCB Central Control Room dashboard (app.cpcbccr.com) exposes a
JSON API that the frontend calls. We replicate those calls to download
station data in chunks (max ~30 days per request to respect rate limits).

Usage:
    python -m src.ingest.cpcb_download
    python -m src.ingest.cpcb_download --help

Output: data/raw/cpcb/ directory with one CSV per station per month.

NOTE: This script respects CPCB's public access. It adds a 2-second
delay between requests and downloads only hourly averages.
Data is used for research/educational purposes.
"""
import argparse
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

MUMBAI_STATIONS = {
    "Bandra Kurla Complex, Mumbai": "site_5029",
    "Colaba, Mumbai": "site_5030",
    "Kurla, Mumbai": "site_5031",
    "Powai, Mumbai": "site_5034",
    "Borivali East, Mumbai": "site_5035",
    "Chembur, Mumbai": "site_5032",
    "Worli, Mumbai": "site_5033",
    "Sion, Mumbai": "site_5036",
    "Andheri East, Mumbai": "site_5037",
    "Mazgaon, Mumbai": "site_5038",
    "Malad West, Mumbai": "site_5039",
    "Vile Parle West, Mumbai": "site_5040",
    "Navi Mumbai": "site_5041",
}

CPCB_API_URL = "https://app.cpcbccr.com/ccr_docs/ccr_docs/station_list_data"
POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "Ozone", "NH3",
              "AT", "RH", "WS", "WD", "BP", "SR", "RF"]

RAW_DIR = Path("data/raw/cpcb")


def fetch_station_data(station_id: str, start_date: str, end_date: str,
                       criteria: str = "24 Hours") -> dict | None:
    """Fetch data from CPCB API for one station and date range."""
    payload = {
        "station_id": station_id,
        "from_date": start_date,
        "to_date": end_date,
        "criteria": criteria,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "CityPulse-Research/1.0",
    }
    try:
        resp = requests.post(CPCB_API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  HTTP {resp.status_code} for {station_id} ({start_date} - {end_date})")
            return None
    except requests.RequestException as e:
        print(f"  Request error for {station_id}: {e}")
        return None


def parse_cpcb_response(raw_json: dict, station_name: str) -> pd.DataFrame:
    """Parse the CPCB JSON response into a clean DataFrame."""
    if not raw_json:
        return pd.DataFrame()

    records = []
    if isinstance(raw_json, list):
        data_list = raw_json
    elif isinstance(raw_json, dict):
        data_list = raw_json.get("data", raw_json.get("tabularData", []))
        if isinstance(data_list, dict):
            data_list = [data_list]
    else:
        return pd.DataFrame()

    if not data_list:
        return pd.DataFrame()

    for entry in data_list:
        if not isinstance(entry, dict):
            continue
        record = {"station": station_name}
        for key in ["from_date", "date", "sampling_date", "From Date"]:
            if key in entry:
                record["timestamp"] = entry[key]
                break
        for key, val in entry.items():
            if key in ("station_id", "from_date", "to_date", "date"):
                continue
            record[key] = val
        records.append(record)

    return pd.DataFrame(records)


def download_station(station_name: str, station_id: str,
                     start: datetime, end: datetime,
                     chunk_days: int = 30) -> pd.DataFrame:
    """Download data for one station in monthly chunks."""
    all_frames = []
    current = start

    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days), end)
        start_str = current.strftime("%d-%b-%Y")
        end_str = chunk_end.strftime("%d-%b-%Y")

        cache_file = RAW_DIR / f"{station_id}_{current.strftime('%Y%m')}.json"
        if cache_file.exists():
            print(f"  [CACHED] {station_name}: {start_str} to {end_str}")
            with open(cache_file, "r") as f:
                raw = json.load(f)
        else:
            print(f"  [DOWNLOAD] {station_name}: {start_str} to {end_str}")
            raw = fetch_station_data(station_id, start_str, end_str)
            if raw:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_file, "w") as f:
                    json.dump(raw, f)
            time.sleep(2)

        if raw:
            df = parse_cpcb_response(raw, station_name)
            if not df.empty:
                all_frames.append(df)

        current = chunk_end + timedelta(days=1)

    if all_frames:
        return pd.concat(all_frames, ignore_index=True)
    return pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description="Download CPCB Mumbai AQ data")
    parser.add_argument("--start", default="2023-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2025-12-31", help="End date YYYY-MM-DD")
    parser.add_argument("--stations", nargs="*", help="Station names (default: all)")
    args = parser.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    stations = args.stations or list(MUMBAI_STATIONS.keys())
    all_data = []

    for name in stations:
        sid = MUMBAI_STATIONS.get(name)
        if not sid:
            print(f"Unknown station: {name}")
            continue
        print(f"\n--- {name} ({sid}) ---")
        df = download_station(name, sid, start, end)
        if not df.empty:
            all_data.append(df)
            print(f"  Got {len(df)} records")
        else:
            print(f"  No data returned")

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        out_path = RAW_DIR / "cpcb_mumbai_combined.csv"
        combined.to_csv(out_path, index=False)
        print(f"\nSaved {len(combined)} records to {out_path}")
    else:
        print("\nNo data downloaded. The CPCB API may require authentication or be unavailable.")
        print("Alternative: Download manually from https://app.cpcbccr.com/ccr/#/caaqm-dashboard-all/caaqm-landing")
        print("Or use the OpenAQ data source instead.")


if __name__ == "__main__":
    main()
