"""Runtime Mumbai feeds and strict freshness/quality checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests

IST = ZoneInfo("Asia/Kolkata")
LAT, LON = 19.0760, 72.8777
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OFFICIAL_AIR_URL = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"


@dataclass
class Feed:
    name: str
    url: str
    license: str
    data: pd.DataFrame
    current: dict
    current_time: pd.Timestamp | None
    min_time: pd.Timestamp | None
    max_time: pd.Timestamp | None
    gaps: int
    duplicates: int
    missing_values: int
    status: str
    note: str = ""


def _get_json(url: str, params: dict, headers: dict | None = None) -> dict:
    response = requests.get(url, params=params, headers=headers, timeout=25)
    response.raise_for_status()
    return response.json()


def _time(value: object) -> pd.Timestamp | None:
    if value is None or value == "":
        return None
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return None
    return timestamp.tz_localize(IST) if timestamp.tzinfo is None else timestamp.tz_convert(IST)


def _open_meteo_feed(name: str, url: str, variables: dict[str, str], *, air: bool = False) -> Feed:
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": ",".join(variables),
        "current": ",".join(variables),
        "past_days": 30,
        "forecast_days": 0,
        "timezone": "Asia/Kolkata",
    }
    if air:
        params["domains"] = "cams_global"
    payload = _get_json(url, params)
    hourly = payload.get("hourly") or {}
    units = payload.get("hourly_units") or {}
    for column, expected_unit in variables.items():
        if units.get(column) != expected_unit:
            raise ValueError(f"{name}: {column} unit {units.get(column)!r}, expected {expected_unit!r}")
    frame = pd.DataFrame(hourly)
    if frame.empty or "time" not in frame:
        raise ValueError(f"{name}: no hourly records")
    frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
    if frame["time"].isna().any():
        raise ValueError(f"{name}: invalid hourly timestamps")
    duplicates = int(frame["time"].duplicated().sum())
    frame = frame.drop_duplicates("time").sort_values("time")
    now = pd.Timestamp.now(tz=IST)
    # Keep only elapsed hours: a forecast timestamp is not a latest observation.
    frame = frame[frame["time"] <= now.tz_localize(None)].copy()
    for column in variables:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if (frame[column].dropna() < 0).any() and column not in ("temperature_2m",):
            raise ValueError(f"{name}: negative {column} values")
    gaps = int((frame["time"].diff().dropna() > pd.Timedelta(hours=1)).sum())
    missing_values = int(frame[list(variables)].isna().sum().sum())
    current = payload.get("current") or {}
    current_time = _time(current.get("time"))
    if current_time is not None and current_time > now + pd.Timedelta(minutes=5):
        raise ValueError(f"{name}: future current timestamp")
    minimum = _time(frame["time"].min()) if not frame.empty else None
    maximum = _time(frame["time"].max()) if not frame.empty else None
    latest = max((x for x in (current_time, maximum) if x is not None), default=None)
    status = "Fresh" if latest is not None and latest >= now - pd.Timedelta(hours=48) else "Stale"
    note = "Issuance time is not exposed by this API; timestamps are data valid times."
    return Feed(name, url, "CC BY 4.0 (attribution); free API tier is non-commercial", frame,
                current, current_time, minimum, maximum, gaps, duplicates, missing_values, status, note)


def fetch_weather() -> Feed:
    return _open_meteo_feed("Open-Meteo weather model", WEATHER_URL, {
        "temperature_2m": "°C", "relative_humidity_2m": "%",
        "precipitation": "mm", "wind_speed_10m": "km/h",
    })


def fetch_modeled_air() -> Feed:
    return _open_meteo_feed("Open-Meteo / CAMS global modeled air quality", AIR_URL, {
        "pm2_5": "μg/m³", "pm10": "μg/m³",
    }, air=True)


def fetch_official_air(api_key: str) -> Feed:
    """Fetch current CPCB station pollutant readings via data.gov.in; never infer AQI."""
    payload = _get_json(OFFICIAL_AIR_URL, {
        "api-key": api_key, "format": "json", "limit": 1000,
        "filters[city]": "Mumbai",
    })
    records = pd.DataFrame(payload.get("records") or [])
    if records.empty:
        raise ValueError("data.gov.in returned no Mumbai station records")
    date_field = next((c for c in ("last_update", "last_updated", "timestamp") if c in records), None)
    if date_field is None:
        raise ValueError("data.gov.in response has no per-record timestamp")
    records["time"] = pd.to_datetime(records[date_field], errors="coerce", dayfirst=True)
    records = records.dropna(subset=["time"])
    if records.empty:
        raise ValueError("data.gov.in returned no dated Mumbai records")
    now = pd.Timestamp.now(tz=IST)
    records["time"] = records["time"].apply(_time)
    records = records[records["time"] <= now]
    if records.empty:
        raise ValueError("data.gov.in returned no valid, nonfuture Mumbai records")
    keys = [c for c in ("station", "pollutant_id", "time") if c in records]
    duplicates = int(records.duplicated(keys).sum()) if keys else 0
    records = records.drop_duplicates(keys) if keys else records
    minimum, maximum = records["time"].min(), records["time"].max()
    status = "Fresh" if maximum >= now - pd.Timedelta(hours=48) else "Stale"
    return Feed("CPCB via data.gov.in", OFFICIAL_AIR_URL, "NDSAP / India Government Open Data",
                records, {}, maximum, minimum, maximum, 0, duplicates, 0, status,
                "Latest station snapshot only; hourly gaps cannot be assessed from this endpoint.")
