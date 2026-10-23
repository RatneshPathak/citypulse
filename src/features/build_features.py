"""
Feature Engineering Pipeline — CityPulse: Mumbai

Constructs strictly leak-free feature vectors for next-day air quality forecasting
and risk classification.

Decision Time Convention:
Forecast for Day t is made at 23:59 IST on Day t-1.
Therefore:
- Day t target: aqi_mean on Day t.
- Available features at decision time:
  1. Autoregressive lags: aqi_mean on Day t-1, Day t-2, Day t-3, Day t-7 (same day last week).
  2. Rolling summary statistics over past 7 days (t-1 to t-7): rolling mean, std, min, max, trend (slope).
  3. Station characteristics: zone one-hot, environmental type, coastal flag, station baseline mean.
  4. Weather forecast features for Day t:
     In real-world deployment, numerical weather predictions (NWP) for Day t (temperature, humidity,
     wind u/v, rain, pressure) are available 24-48 hours ahead from IMD / Open-Meteo.
     We use Day t weather variables as the operational weather forecast.
  5. Calendar features: cyclical day of year (sin/cos), cyclical day of week (sin/cos), month indicators,
     monsoon season flag, winter season flag, festival/Diwali window indicator.

Strict Leakage Prevention:
- Rolling statistics strictly exclude Day t (closed='left' / shift(1)).
- Imputation and scaling parameters are fit STRICTLY on training split and applied to test split.
- No random shuffling anywhere.

Usage:
    python -m src.features.build_features
"""
import logging
from pathlib import Path
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROCESSED_DAILY = Path("data/processed/mumbai_aqi_daily_clean.parquet")
FEATURES_DIR = Path("data/processed")

def construct_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build feature table for all stations."""
    logging.info("Building leak-free feature set across monitoring stations...")
    station_counts = df.groupby("canonical_station")["is_cpcb_valid"].sum()
    valid_stations = station_counts[station_counts >= 150].index.tolist()
    logging.info(f"Retaining {len(valid_stations)} stations with >= 150 valid CPCB days")

    df_filtered = df[df["canonical_station"].isin(valid_stations)].copy()
    df_filtered["date"] = pd.to_datetime(df_filtered["date"])
    df_filtered = df_filtered.sort_values(["canonical_station", "date"]).reset_index(drop=True)

    station_frames = []
    for station, group in df_filtered.groupby("canonical_station"):
        grp = group.copy().sort_values("date")

        full_idx = pd.date_range(grp["date"].min(), grp["date"].max(), freq="D")
        grp = grp.set_index("date").reindex(full_idx)
        grp["canonical_station"] = station
        grp["date"] = grp.index

        grp["target_next_day_aqi"] = grp["aqi_mean"]
        grp["target_next_day_unhealthy"] = (grp["aqi_mean"] > 200).astype(int)

        grp["lag_1_aqi"] = grp["aqi_mean"].shift(1)
        grp["lag_2_aqi"] = grp["aqi_mean"].shift(2)
        grp["lag_3_aqi"] = grp["aqi_mean"].shift(3)
        grp["lag_7_aqi"] = grp["aqi_mean"].shift(7)

        shifted_series = grp["aqi_mean"].shift(1)
        grp["rolling_mean_7d"] = shifted_series.rolling(window=7, min_periods=3).mean()
        grp["rolling_std_7d"] = shifted_series.rolling(window=7, min_periods=3).std()
        grp["rolling_min_7d"] = shifted_series.rolling(window=7, min_periods=3).min()
        grp["rolling_max_7d"] = shifted_series.rolling(window=7, min_periods=3).max()
        grp["trend_7d"] = grp["lag_1_aqi"] - grp["rolling_mean_7d"]

        weather_cols = ["temp_mean", "humidity_mean", "wind_speed_mean", "wind_u_mean", "wind_v_mean", "rain_total_mm", "pressure_mean"]
        for wc in weather_cols:
            if wc in grp.columns:
                grp[f"prior_day_{wc}"] = grp[wc].shift(1).ffill(limit=2)

        if "prior_day_wind_speed_mean" in grp and "prior_day_pressure_mean" in grp:
            grp["prior_day_stagnation_index"] = (grp["prior_day_pressure_mean"] / 1013.25) * (1.0 / np.maximum(grp["prior_day_wind_speed_mean"], 1.0))

        day_of_year = grp["date"].dt.dayofyear
        grp["doy_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
        grp["doy_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)

        day_of_week = grp["date"].dt.weekday
        grp["dow_sin"] = np.sin(2 * np.pi * day_of_week / 7)
        grp["dow_cos"] = np.cos(2 * np.pi * day_of_week / 7)
        grp["is_weekend"] = day_of_week.isin([5, 6]).astype(int)

        month = grp["date"].dt.month
        grp["is_monsoon"] = month.isin([6, 7, 8, 9]).astype(int)
        grp["is_winter"] = month.isin([12, 1, 2]).astype(int)

        diwali_days = [
            (pd.to_datetime("2021-11-02"), pd.to_datetime("2021-11-07")),
            (pd.to_datetime("2022-10-22"), pd.to_datetime("2022-10-27")),
            (pd.to_datetime("2023-11-10"), pd.to_datetime("2023-11-15")),
        ]
        grp["is_diwali_window"] = 0
        for s, e in diwali_days:
            grp.loc[(grp["date"] >= s) & (grp["date"] <= e), "is_diwali_window"] = 1

        for meta_col in ["zone", "env_type", "is_coastal", "latitude", "longitude"]:
            if meta_col in grp.columns:
                grp[meta_col] = grp[meta_col].bfill().ffill()

        station_frames.append(grp.reset_index(drop=True))

    feature_df = pd.concat(station_frames, ignore_index=True)

    valid_mask = feature_df["target_next_day_aqi"].notna() & feature_df["lag_1_aqi"].notna()
    feature_df_clean = feature_df[valid_mask].copy()

    logging.info(f"Constructed feature table with {len(feature_df_clean):,} valid rows and {len(feature_df_clean.columns)} columns")
    return feature_df_clean

def main():
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    daily_df = pd.read_parquet(PROCESSED_DAILY)

    feature_df = construct_features(daily_df)
    out_path = FEATURES_DIR / "mumbai_features_model_ready.parquet"
    feature_df.to_parquet(out_path, index=False)
    logging.info(f"Saved model-ready features to {out_path}")

if __name__ == "__main__":
    main()
