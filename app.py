"""CityPulse Mumbai: current, dated public feeds only."""

from __future__ import annotations

import os
from datetime import timedelta

import pandas as pd
import streamlit as st

from src.live_sources import AIR_URL, OFFICIAL_AIR_URL, WEATHER_URL, Feed, fetch_modeled_air, fetch_official_air, fetch_weather

st.set_page_config(page_title="CityPulse Mumbai", page_icon="🌆", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def weather_feed() -> Feed:
    return fetch_weather()


@st.cache_data(ttl=3600, show_spinner=False)
def modeled_air_feed() -> Feed:
    return fetch_modeled_air()


@st.cache_data(ttl=3600, show_spinner=False)
def official_air_feed(api_key: str) -> Feed:
    return fetch_official_air(api_key)


def stamp(feed: Feed, *, current: bool = False) -> None:
    moment = feed.current_time if current else feed.max_time
    date = moment.strftime("%d %b %Y, %H:%M IST") if moment is not None else "unknown"
    st.caption(f"Data last updated: {date} | Source: {feed.name} · [API]({feed.url})")


def issue(feed: Feed) -> None:
    if feed.status != "Fresh":
        st.warning(f"No recent data from {feed.name}. Latest record: {feed.max_time}.")
    if feed.gaps or feed.duplicates or feed.missing_values:
        st.caption(f"Quality check: {feed.gaps} hourly gaps; {feed.duplicates} duplicate timestamps removed; {feed.missing_values} missing values. Missing values are not filled.")


def registry_row(label: str, source: str, updated: str, latest: str, status: str, license: str, period: str = "—", checks: str = "—") -> dict:
    return {"Dataset": label, "Source": source, "Last updated": updated,
            "Latest record date": latest, "Status": status, "License": license,
            "Data range": period, "Quality check": checks}


def main() -> None:
    st.title("CityPulse Mumbai")
    st.caption("Current Mumbai weather and air quality, with source and record dates shown for every panel. Times are IST.")
    st.info("Particulate values below are **CAMS model estimates**, not CPCB station measurements or India AQI. The historical 2021–2023 model dashboard is retired from the main app.")

    today = pd.Timestamp.now(tz="Asia/Kolkata").date()
    start = st.sidebar.date_input("From", value=today - timedelta(days=30), min_value=today - timedelta(days=30), max_value=today)
    end = st.sidebar.date_input("Through", value=today, min_value=start, max_value=today)
    st.sidebar.caption("Live APIs expose a rolling 30-day window. Values outside it are not backfilled from bundled files.")
    if st.sidebar.button("Refresh now"):
        weather_feed.clear()
        modeled_air_feed.clear()
        official_air_feed.clear()
        st.rerun()

    feeds: list[Feed] = []
    errors: dict[str, str] = {}
    for label, loader in (("Weather", weather_feed), ("Modeled air", modeled_air_feed)):
        try:
            feeds.append(loader())
        except Exception as exc:
            errors[label] = str(exc)

    weather = next((x for x in feeds if x.url == WEATHER_URL), None)
    air = next((x for x in feeds if x.url == AIR_URL), None)

    st.subheader("Weather")
    if weather and weather.status == "Fresh":
        cols = st.columns(4)
        for col, (label, field, unit) in zip(cols, (
            ("Temperature", "temperature_2m", "°C"), ("Humidity", "relative_humidity_2m", "%"),
            ("Precipitation", "precipitation", "mm"), ("Wind speed", "wind_speed_10m", "km/h"),
        )):
            value = weather.current.get(field)
            col.metric(label, f"{value} {unit}" if value is not None else "No recent data")
            with col:
                stamp(weather, current=True)
        view = weather.data.loc[weather.data["time"].dt.date.between(start, end), ["time", "temperature_2m", "precipitation"]]
        if view.empty:
            st.warning("No recent weather records in the selected period.")
        else:
            st.line_chart(view.set_index("time")["temperature_2m"], y_label="Temperature (°C)")
            stamp(weather)
            st.bar_chart(view.set_index("time")["precipitation"], y_label="Precipitation (mm/hour)")
            stamp(weather)
        issue(weather)
    else:
        st.warning("No recent weather data. " + errors.get("Weather", "Source is stale."))

    st.subheader("Modeled particulate concentrations")
    if air and air.status == "Fresh":
        c1, c2 = st.columns(2)
        for col, field, label in ((c1, "pm2_5", "PM2.5"), (c2, "pm10", "PM10")):
            value = air.current.get(field)
            col.metric(label, f"{value} μg/m³" if value is not None else "No recent data")
            with col:
                stamp(air, current=True)
        view = air.data.loc[air.data["time"].dt.date.between(start, end), ["time", "pm2_5", "pm10"]]
        if view.empty:
            st.warning("No recent modeled air records in the selected period.")
        else:
            st.line_chart(view.set_index("time")[["pm2_5", "pm10"]], y_label="Modeled concentration (μg/m³)")
            stamp(air)
        st.caption("CAMS global grid is about 45 km; values cannot resolve individual streets or wards. Attribution: Open-Meteo and Copernicus Atmosphere Monitoring Service.")
        issue(air)
    else:
        st.warning("No recent modeled air data. " + errors.get("Modeled air", "Source is stale."))

    st.subheader("Official station air quality")
    key = os.getenv("DATA_GOV_IN_KEY", "")
    if not key:
        try:
            key = st.secrets.get("DATA_GOV_IN_KEY", "")
        except FileNotFoundError:
            key = ""
    official = None
    if key:
        try:
            official = official_air_feed(key)
            if official.status == "Fresh":
                st.dataframe(official.data, hide_index=True, width="stretch")
                stamp(official)
                issue(official)
            else:
                st.warning("No recent CPCB station records returned; older records are withheld.")
        except Exception as exc:
            errors["Official air"] = str(exc)
            st.warning(f"No recent CPCB station records could be verified: {exc}")
    else:
        st.warning("Needs API key: set `DATA_GOV_IN_KEY` (free data.gov.in key) for CPCB station readings. OpenAQ v3 is another option and requires `OPENAQ_API_KEY`. No older AQI is substituted.")

    st.subheader("Availability of other city data")
    st.write("Traffic, ward activity, and OSM map layers have no verified current machine-readable response in this run, so these panels are withheld. The [BMC Civic Diary 2026](https://portal.mcgm.gov.in/irj/go/km/docs/documents/HomePage%20Data/BMC%20Diary/BMC_English%20Diary_2026.pdf) contains **mid-year 2025 population estimates**, which are historical under the 12-month rule; they are not a live population count.")

    rows = []
    for label, feed in (("Weather", weather), ("Modeled PM2.5 / PM10", air), ("Official CPCB station readings", official)):
        if feed:
            updated = feed.current_time.strftime("%Y-%m-%d %H:%M IST") if feed.current_time is not None else "Not exposed"
            latest = feed.max_time.strftime("%Y-%m-%d %H:%M IST") if feed.max_time is not None else "None"
            period = f"{feed.min_time:%Y-%m-%d} to {feed.max_time:%Y-%m-%d}" if feed.min_time is not None and feed.max_time is not None else "None"
            rows.append(registry_row(label, feed.url, updated, latest, feed.status, feed.license, period,
                                     f"{feed.gaps} gaps; {feed.duplicates} duplicates; {feed.missing_values} missing values; units checked" if label != "Official CPCB station readings" else feed.note))
        else:
            url = OFFICIAL_AIR_URL if label.startswith("Official") else WEATHER_URL if label == "Weather" else AIR_URL
            status = "Needs API key" if label.startswith("Official") and not key else "Unavailable"
            rows.append(registry_row(label, url, "Unverified", "Unverified", status, "See source terms", checks=errors.get(label, "No response verified")))
    rows.extend([
        registry_row("Mumbai traffic", "Mumbai Traffic Police / MMRDA / BEST", "Unverified", "Unverified", "Unavailable", "Unverified", checks="No dated public API verified"),
        registry_row("Ward activity", "BMC / Maharashtra open data", "Unverified", "Unverified", "Unavailable", "Unverified", checks="No dated current records verified"),
        registry_row("OSM map features", "https://overpass-api.de/api/interpreter", "Unverified", "Unverified", "Unavailable", "ODbL 1.0", checks="Live query returned HTTP 406; alternate instance rate-limited/timed out"),
        registry_row("Population estimate", "BMC Civic Diary 2026", "2026 publication", "Mid-year 2025 estimate", "Stale", "Official publication; reuse terms unverified", "2025", "Reference year shown; no live count"),
    ])
    st.subheader("Source and freshness register")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("API responses do not expose model issuance time; the displayed update is the latest value's valid time. No missing records are filled. Sources are rechecked hourly.")


if __name__ == "__main__":
    main()
