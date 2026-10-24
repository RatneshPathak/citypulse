# Current data policy (audited 24 October 2026)

The Streamlit app fetches data at runtime. Its two keyless feeds are cached for one hour. It never uses bundled 2021–2023 CSV/Parquet files in live metrics, never shifts record dates, and never fills missing recent values with older data. The default chart window is the last 30 days. An API response more than 48 hours old is withheld from the live panels; the requested one-year cutoff is therefore also satisfied.

| Dataset | Source and URL | License / terms | Source last updated | Verified data range and latest record | Status on 24 October 2026 |
| --- | --- | --- | --- | --- | --- |
| Weather | [Open-Meteo forecast API](https://open-meteo.com/en/docs) | Data CC BY 4.0; keyless tier limited to non-commercial use | API does not expose model issuance time | 24 Sep–23 Oct 2026 hourly; current value 24 Oct 2026 09:45 IST | Fresh |
| Modeled PM2.5 and PM10 | [Open-Meteo air quality API / CAMS global](https://open-meteo.com/en/docs/air-quality-api) | CC BY 4.0; attribute Open-Meteo and CAMS; keyless tier limited to non-commercial use | API does not expose model issuance time; CAMS global updates every 12 hours | 24 Sep–23 Oct 2026 hourly; current value 24 Oct 2026 09:30 IST | Fresh |
| Official station pollutants | [CPCB data.gov.in resource](https://www.data.gov.in/catalog/real-time-air-quality-index) | NDSAP government open data | Catalog was updated 23 Oct 2026; per-record date unverified without key | Unverified until a key is supplied | Needs API key (`DATA_GOV_IN_KEY`) |
| OpenAQ station pollutants | [OpenAQ v3](https://docs.openaq.org/using-the-api/quick-start) | Underlying provider terms vary | Unverified without key | Unverified until a key is supplied | Needs API key (`OPENAQ_API_KEY`); not wired as a fallback |
| Mumbai traffic | Mumbai Traffic Police, MMRDA, BEST searched | Unverified | Unverified | No verified machine-readable recent traffic records | Unavailable |
| Ward activity | BMC / Maharashtra open data searched | Unverified | Unverified | No verified current per-ward time series | Unavailable |
| OSM map features | [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) | ODbL 1.0 | Unverified | Primary instance returned HTTP 406; alternate instance rate-limited or timed out | Unavailable |
| Population estimate | [BMC Civic Diary 2026](https://portal.mcgm.gov.in/irj/go/km/docs/documents/HomePage%20Data/BMC%20Diary/BMC_English%20Diary_2026.pdf) | Official publication; reuse terms unverified | Published 2026 | Mid-year 2025 estimate, older than 24 Oct 2025 cutoff | Stale; reference only |

Open-Meteo air values are **45 km CAMS global model estimates**, not CPCB observations and not India's AQI. Weather is model output too. Do not combine those units with an AQI index. The live request checks units, timestamps, duplicate hours, missing hours, and negative values. The data API does not provide issuance times; the UI labels the latest **data valid time**, not a verified publication time.

The repository's processed AQI and forecast files end on 31 Dec 2023. They are historical research artifacts and are excluded from the live app. A separate CPCB snapshot file ends on 31 Dec 2025 but cannot substitute for today's readings. The old dashboard had advanced 2023 dates to the present, so its entry point was replaced.

## Setup

Run `streamlit run app.py`. Optionally set `DATA_GOV_IN_KEY` as an environment variable or Streamlit secret to request the CPCB resource. The key is obtained from [data.gov.in](https://www.data.gov.in/). The app verifies each returned station timestamp before showing it. If the key or live response is unavailable, the app shows a data gap and retains no stale fallback.
