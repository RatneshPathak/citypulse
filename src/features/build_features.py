"""
Feature Engineering Pipeline — CityPulse: Mumbai

Constructs strictly leak-free feature vectors for next-day air quality forecasting
and risk classification.

Decision Time Convention:
Forecast for Day t is made at 23:59 IST on Day t-1.
Therefore:
- Day t target: aqi_mean on Day t.
- Available features at decision time:
  1. Autoregressive lags: aqi_mean on Day t-1, t-2, t-3, t-7, t-14.
  2. Rolling summary statistics over past 7d and 14d (window ends at t-1).
  3. AQI delta features: day-on-day and week-on-week changes in lag_1.
  4. Station expanding mean: mean of all aqi_mean up to and including t-1
     (per station, expanding window, shifted by 1 day — no t-day data).
  5. Station characteristics: coastal flag, lat/lon.
  6. Prior-day weather (t-1): temperature, humidity, wind speed, wind u/v,
     rain, pressure, stagnation index.
  7. Calendar features: cyclical day-of-year and day-of-week (sin/cos),
     raw month integer, weekend flag, monsoon flag, winter flag,
     Diwali window flag, Holi window flag.

Leakage controls:
- All rolling statistics end at t-1 (shift(1) before rolling).
- Prior-day weather uses shift(1) with forward-fill capped at 2 days.
- Station expanding mean uses shift(1) before expanding().mean().
- No imputation/scaling parameters are fit here; that happens in the training
  pipeline on training data only.
- No random shuffling.

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
    """
    Build leak-free feature table for all monitoring stations.

    Parameters
    ----------
    df : pd.DataFrame
        Daily processed AQI + weather data from the cleaning pipeline.

    Returns
    -------
    pd.DataFrame
        One row per (station, date) with all feature columns and targets.
        Rows where target or lag_1 are missing are dropped.
    """
    logging.info("Building leak-free feature set across monitoring stations...")
    station_counts = df.groupby("canonical_station")["is_cpcb_valid"].sum()
    valid_stations = station_counts[station_counts >= 150].index.tolist()
    logging.info(f"Retaining {len(valid_stations)} stations with >= 150 valid CPCB days")

    df_filtered = df[df["canonical_station"].isin(valid_stations)].copy()
    df_filtered["date"] = pd.to_datetime(df_filtered["date"])
    df_filtered = df_filtered.sort_values(["canonical_station", "date"]).reset_index(drop=True)

    _HOLI_MAIN_DAYS = [
        pd.Timestamp("2021-03-29"),
        pd.Timestamp("2022-03-18"),
        pd.Timestamp("2023-03-08"),
    ]
    _HOLI_WINDOW_DATES = set()
    for holi_day in _HOLI_MAIN_DAYS:
        for delta in range(-1, 2):
            _HOLI_WINDOW_DATES.add(holi_day + pd.Timedelta(days=delta))

    _DIWALI_RANGES = [
        (pd.Timestamp("2021-11-02"), pd.Timestamp("2021-11-07")),
        (pd.Timestamp("2022-10-22"), pd.Timestamp("2022-10-27")),
        (pd.Timestamp("2023-11-10"), pd.Timestamp("2023-11-15")),
    ]

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
        grp["lag_14_aqi"] = grp["aqi_mean"].shift(14)

        _shifted = grp["aqi_mean"].shift(1)
        grp["rolling_mean_7d"]  = _shifted.rolling(window=7,  min_periods=3).mean()
        grp["rolling_std_7d"]   = _shifted.rolling(window=7,  min_periods=3).std()
        grp["rolling_min_7d"]   = _shifted.rolling(window=7,  min_periods=3).min()
        grp["rolling_max_7d"]   = _shifted.rolling(window=7,  min_periods=3).max()
        grp["trend_7d"]         = grp["lag_1_aqi"] - grp["rolling_mean_7d"]
        grp["rolling_mean_14d"] = _shifted.rolling(window=14, min_periods=7).mean()
        grp["rolling_std_14d"]  = _shifted.rolling(window=14, min_periods=7).std()

        grp["aqi_delta_1d"] = grp["lag_1_aqi"] - grp["lag_2_aqi"]
        grp["aqi_delta_7d"] = grp["lag_1_aqi"] - grp["lag_7_aqi"]

        grp["station_expanding_mean_aqi"] = (
            grp["aqi_mean"].shift(1).expanding(min_periods=14).mean()
        )

        weather_cols = [
            "temp_mean", "humidity_mean", "wind_speed_mean",
            "wind_u_mean", "wind_v_mean", "rain_total_mm", "pressure_mean",
        ]
        for wc in weather_cols:
            if wc in grp.columns:
                grp[f"prior_day_{wc}"] = grp[wc].shift(1).ffill(limit=2)

        if "prior_day_wind_speed_mean" in grp.columns and "prior_day_pressure_mean" in grp.columns:
            grp["prior_day_stagnation_index"] = (
                (grp["prior_day_pressure_mean"] / 1013.25)
                / np.maximum(grp["prior_day_wind_speed_mean"], 1.0)
            )

        day_of_year = grp["date"].dt.dayofyear
        grp["doy_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
        grp["doy_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)

        day_of_week = grp["date"].dt.weekday
        grp["dow_sin"] = np.sin(2 * np.pi * day_of_week / 7)
        grp["dow_cos"] = np.cos(2 * np.pi * day_of_week / 7)
        grp["is_weekend"] = day_of_week.isin([5, 6]).astype(int)

        month = grp["date"].dt.month
        grp["month"] = month.astype(int)
        grp["is_monsoon"] = month.isin([6, 7, 8, 9]).astype(int)
        grp["is_winter"]  = month.isin([12, 1, 2]).astype(int)

        grp["is_diwali_window"] = 0
        for diwali_start, diwali_end in _DIWALI_RANGES:
            mask = (grp["date"] >= diwali_start) & (grp["date"] <= diwali_end)
            grp.loc[mask, "is_diwali_window"] = 1

        grp["is_holi_window"] = grp["date"].isin(_HOLI_WINDOW_DATES).astype(int)

        for meta_col in ["zone", "env_type", "is_coastal", "latitude", "longitude"]:
            if meta_col in grp.columns:
                grp[meta_col] = grp[meta_col].bfill().ffill()

        station_frames.append(grp.reset_index(drop=True))

    feature_df = pd.concat(station_frames, ignore_index=True)

    valid_mask = (
        feature_df["target_next_day_aqi"].notna()
        & feature_df["lag_1_aqi"].notna()
    )
    feature_df_clean = feature_df[valid_mask].copy()

    logging.info(
        f"Constructed feature table with {len(feature_df_clean):,} valid rows "
        f"and {len(feature_df_clean.columns)} columns"
    )
    return feature_df_clean


def main() -> None:
    """Regenerate the model-ready feature parquet from the cleaned daily data."""
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    daily_df = pd.read_parquet(PROCESSED_DAILY)

    feature_df = construct_features(daily_df)
    out_path = FEATURES_DIR / "mumbai_features_model_ready.parquet"
    feature_df.to_parquet(out_path, index=False)
    logging.info(f"Saved model-ready features to {out_path}")
    logging.info(f"Columns: {list(feature_df.columns)}")


if __name__ == "__main__":
    main()
