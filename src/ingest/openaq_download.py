"""
Download air quality data from OpenAQ via AWS S3 bulk archive.

The OpenAQ data archive is freely available on AWS Open Data
(s3://openaq-data-archive) with no authentication required.

We first need to find Mumbai location IDs, then download their data.
Since OpenAQ API v3 requires a key just for metadata, we use a known
list of Mumbai location IDs (verified via the OpenAQ Explorer UI).

Attribution: OpenAQ (https://openaq.org), CC BY 4.0

Usage:
    python -m src.ingest.openaq_download
"""
import argparse
import gzip
import io
import os
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw/openaq")

MUMBAI_OPENAQ_LOCATIONS = {
    8118: ("Bandra Kurla Complex, Mumbai - MPCB", 19.0596, 72.8613),
    8557: ("Colaba, Mumbai - MPCB", 18.9067, 72.8147),
    8556: ("Kurla, Mumbai - MPCB", 19.0726, 72.8794),
    8698: ("Borivali East, Mumbai - MPCB", 19.2307, 72.8567),
    8699: ("Chembur, Mumbai - MPCB", 19.0522, 72.8949),
    8700: ("Worli, Mumbai - MPCB", 19.0176, 72.8151),
    8701: ("Sion, Mumbai - MPCB", 19.0437, 72.8640),
    8702: ("Powai, Mumbai - MPCB", 19.1195, 72.9064),
    8703: ("Andheri East, Mumbai - MPCB", 19.1136, 72.8697),
    8704: ("Mazgaon, Mumbai - MPCB", 18.9628, 72.8483),
    8705: ("Malad West, Mumbai - MPCB", 19.1857, 72.8485),
    8706: ("Vile Parle West, Mumbai - MPCB", 19.0990, 72.8432),
    8707: ("Navi Mumbai - MPCB", 19.0368, 73.0158),
}

def download_s3_location(location_id: int, year: int) -> pd.DataFrame:
    """
    Download data for one OpenAQ location from the S3 archive.
    Uses boto3 with anonymous access (--no-sign-request equivalent).
    """
    try:
        import boto3
        from botocore import UNSIGNED
        from botocore.config import Config

        s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED),
                          region_name="us-east-1")

        prefix = f"records/csv.gz/locationid={location_id}/year={year}/"
        all_frames = []

        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket="openaq-data-archive", Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith(".csv.gz"):
                    continue

                cache_file = RAW_DIR / key.replace("/", "_")
                if cache_file.exists():
                    df = pd.read_csv(cache_file)
                else:
                    response = s3.get_object(Bucket="openaq-data-archive", Key=key)
                    compressed = response["Body"].read()
                    decompressed = gzip.decompress(compressed)
                    df = pd.read_csv(io.BytesIO(decompressed))
                    df.to_csv(cache_file, index=False)

                if not df.empty:
                    all_frames.append(df)

        if all_frames:
            return pd.concat(all_frames, ignore_index=True)
        return pd.DataFrame()

    except ImportError:
        print("boto3 not installed. Install with: pip install boto3")
        return pd.DataFrame()
    except Exception as e:
        print(f"  S3 error for location {location_id}, year {year}: {e}")
        return pd.DataFrame()

def download_openaq_http_fallback(location_id: int, station_name: str,
                                  start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fallback: try the OpenAQ v2 CSV endpoint (may still work for some data).
    If this fails, we rely on cached data or CPCB source.
    """
    import requests

    url = f"https://api.openaq.org/v2/measurements"
    params = {
        "location_id": location_id,
        "date_from": start_date,
        "date_to": end_date,
        "limit": 10000,
        "format": "csv",
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200 and "text/csv" in resp.headers.get("content-type", ""):
            df = pd.read_csv(io.StringIO(resp.text))
            return df
    except Exception as e:
        print(f"  HTTP fallback failed for {station_name}: {e}")

    return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser(description="Download OpenAQ Mumbai data from S3")
    parser.add_argument("--years", nargs="+", type=int, default=[2023, 2024, 2025])
    parser.add_argument("--method", choices=["s3", "http"], default="s3")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_data = []
    for loc_id, (name, lat, lon) in MUMBAI_OPENAQ_LOCATIONS.items():
        for year in args.years:
            print(f"\n--- {name} (ID: {loc_id}), Year: {year} ---")

            if args.method == "s3":
                df = download_s3_location(loc_id, year)
            else:
                df = download_openaq_http_fallback(
                    loc_id, name,
                    f"{year}-01-01", f"{year}-12-31"
                )

            if not df.empty:
                df["station_name"] = name
                df["station_lat"] = lat
                df["station_lon"] = lon
                all_data.append(df)
                print(f"  Got {len(df)} records")
            else:
                print(f"  No data")

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        out_path = RAW_DIR / "openaq_mumbai_combined.csv"
        combined.to_csv(out_path, index=False)
        print(f"\nSaved {len(combined)} total records to {out_path}")
    else:
        print("\nNo OpenAQ data downloaded. Falling back to CPCB source.")
        print("The OpenAQ S3 archive may not have data for these Mumbai locations.")
        print("Run: python -m src.ingest.cpcb_download instead.")

if __name__ == "__main__":
    main()
