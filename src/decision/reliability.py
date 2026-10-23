from __future__ import annotations

import pandas as pd


def station_reliability(daily: pd.DataFrame, as_of_date: pd.Timestamp, days: int = 30) -> pd.DataFrame:
    if days < 1:
        raise ValueError("days must be positive")

    end = pd.Timestamp(as_of_date).normalize()
    start = end - pd.Timedelta(days=days - 1)
    frame = daily.loc[:, ["canonical_station", "date", "valid_hours"]].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["valid_hours"] = pd.to_numeric(frame["valid_hours"], errors="coerce").fillna(0).clip(0, 24)
    frame = frame.loc[frame["date"].between(start, end)]
    frame = frame.groupby(["canonical_station", "date"], as_index=False)["valid_hours"].max()

    summary = frame.groupby("canonical_station")["valid_hours"].agg(
        observed_hours="sum",
        valid_days=lambda hours: int((hours >= 18).sum()),
    )
    summary["expected_hours"] = days * 24
    summary["coverage_pct"] = (100 * summary["observed_hours"] / summary["expected_hours"]).round(1)
    summary["missing_hours_pct"] = (100 - summary["coverage_pct"]).round(1)
    summary["confidence"] = "Low"
    summary.loc[(summary["coverage_pct"] >= 75) & (summary["valid_days"] >= 18), "confidence"] = "Medium"
    summary.loc[(summary["coverage_pct"] >= 90) & (summary["valid_days"] >= 24), "confidence"] = "High"
    return summary.reset_index().rename(columns={"canonical_station": "station"})
