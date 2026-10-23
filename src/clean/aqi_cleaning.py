"""
CityPulse: Mumbai — CPCB AQI Cleaning Pipeline
Refactored modular implementation of the team's source-of-truth notebook:
src/CityPulse_AQI_Cleaning_EDA.ipynb.

Core steps:
load_cpcb_excel_files -> standardise_schema -> deduplicate_records -> 
handle_missing_values -> flag_outliers_iqr -> compute_station_statistics -> save_cleaned_data
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import glob
import logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

POLLUTANTS: List[str] = ["PM2.5", "PM10", "NO", "NO2", "NH3", "SO2", "CO"]
FINAL_COLUMNS: List[str] = ["From Date", "To Date", "Station"] + POLLUTANTS

def load_cpcb_excel_file(file_path: Union[str, Path]) -> Tuple[pd.DataFrame, Dict]:
    """
    Parses a single official CPCB Advance Search Excel export.
    
    Extracts metadata from rows 0-9 and tabular pollutant measurements
    starting from header row 10 (11th Excel row).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CPCB Excel file not found: {file_path}")

    raw_header = pd.read_excel(file_path, header=None, nrows=10)
    station_name = str(raw_header.iloc[5, 2]).strip()
    period_start = raw_header.iloc[8, 2]
    period_end = raw_header.iloc[9, 2]

    df = pd.read_excel(file_path, header=10)
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]

    for date_col in ["From Date", "To Date"]:
        if date_col not in df.columns:
            raise ValueError(f"Required date column '{date_col}' missing from {file_path.name}")
        df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")

    for p in POLLUTANTS:
        if p in df.columns:
            df[p] = pd.to_numeric(df[p], errors="coerce")
        else:
            df[p] = np.nan

    df["Station"] = station_name
    df["Source_File"] = file_path.name

    metadata = {
        "file": file_path.name,
        "station": station_name,
        "period_start": period_start,
        "period_end": period_end,
        "raw_rows": len(df),
        "missing_from_date": df["From Date"].isna().sum(),
        "missing_to_date": df["To Date"].isna().sum(),
        "duplicate_timestamps": df.duplicated(subset=["From Date", "To Date"]).sum(),
    }
    return df, metadata

def load_all_cpcb_excel_files(
    directory_or_glob: Union[str, Path] = "data/raw/cpcb"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Finds and loads all CPCB Excel files matching *.xlsx.
    Returns combined raw DataFrame and the file summary audit report.
    """
    path_obj = Path(directory_or_glob)
    if path_obj.is_dir():
        file_paths = sorted(list(path_obj.glob("*.xlsx")) + list(path_obj.glob("Advance_Search_*.xlsx")))
    else:
        file_paths = sorted([Path(p) for p in glob.glob(str(directory_or_glob))])

    if not file_paths:
        logging.warning(f"No CPCB Excel files found in {directory_or_glob}.")
        return pd.DataFrame(), pd.DataFrame()

    dfs = []
    reports = []
    for f in file_paths:
        logging.info(f"Loading CPCB file: {f.name}")
        df_file, meta = load_cpcb_excel_file(f)
        dfs.append(df_file)
        reports.append(meta)

    combined = pd.concat(dfs, ignore_index=True)
    report_df = pd.DataFrame(reports)
    return combined, report_df

def deduplicate_records(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """
    Verifies and drops any duplicate timestamps within each station.
    """
    if df.empty:
        return df, 0
    dup_mask = df.duplicated(subset=["Station", "From Date", "To Date"], keep="first")
    num_dups = int(dup_mask.sum())
    if num_dups > 0:
        logging.warning(f"Removed {num_dups} duplicate records across station-timestamps.")
        df = df[~dup_mask].copy()
    return df, num_dups

def handle_missing_values(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """
    Filters out records where ALL pollutant measurements are missing (offline sensors).
    Preserves partial-missing records without silent synthetic imputation.
    """
    if df.empty:
        return df, 0
    pollutant_cols = [p for p in POLLUTANTS if p in df.columns]
    all_missing_mask = df[pollutant_cols].isna().all(axis=1)
    num_offline = int(all_missing_mask.sum())
    cleaned_df = df.loc[~all_missing_mask].copy()
    logging.info(
        f"Missing value filter: removed {num_offline} offline rows ({num_offline/max(len(df),1)*100:.1f}%), "
        f"retained {len(cleaned_df)} analysis-ready rows."
    )
    return cleaned_df, num_offline

def detect_outliers_iqr(
    df: pd.DataFrame,
    pollutant: str = "PM2.5",
    multiplier: float = 1.5
) -> pd.DataFrame:
    """
    Detects potential statistical outliers per station using the Tukey IQR method:
    [Q1 - 1.5*IQR, Q3 + 1.5*IQR].
    Flags them in an 'is_outlier' column without dropping them.
    """
    if df.empty or pollutant not in df.columns:
        return pd.DataFrame()

    outlier_dfs = []
    for station, group in df.groupby("Station"):
        series = group[pollutant].dropna()
        if series.empty:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        station_outliers = group[
            (group[pollutant] < lower_bound) | (group[pollutant] > upper_bound)
        ][["From Date", "Station", pollutant]].copy()
        station_outliers["lower_bound"] = round(lower_bound, 2)
        station_outliers["upper_bound"] = round(upper_bound, 2)
        outlier_dfs.append(station_outliers)

    if not outlier_dfs:
        return pd.DataFrame()
    return pd.concat(outlier_dfs, ignore_index=True)

def compute_station_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes station-by-station multi-pollutant descriptive summary statistics:
    mean, median, min, max, count.
    """
    if df.empty:
        return pd.DataFrame()
    pollutant_cols = [p for p in POLLUTANTS if p in df.columns]
    stats = (
        df.groupby("Station")[pollutant_cols]
        .agg(["mean", "median", "min", "max", "count"])
        .round(2)
    )
    return stats

def clean_aqi_dataset(
    raw_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Executes the full notebook cleaning sequence top-to-bottom:
    1. Deduplicates records
    2. Drops offline sensor rows (all pollutants NaN)
    3. Flags IQR outliers
    4. Computes station summary statistics
    5. Returns (cleaned_df, outlier_df, summary_stats_df)
    """
    if raw_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    deduped, _ = deduplicate_records(raw_df)
    cleaned, _ = handle_missing_values(deduped)
    
    avail_cols = [c for c in FINAL_COLUMNS if c in cleaned.columns]
    final_cleaned = cleaned[avail_cols].copy()
    
    if "From Date" in final_cleaned.columns and "Station" in final_cleaned.columns:
        final_cleaned = final_cleaned.sort_values(["Station", "From Date"]).reset_index(drop=True)

    outliers = detect_outliers_iqr(final_cleaned, pollutant="PM2.5")
    stats = compute_station_statistics(final_cleaned)

    return final_cleaned, outliers, stats

def run_pipeline(
    raw_dir: Union[str, Path] = "data/raw/cpcb",
    output_dir: Union[str, Path] = "data/processed",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Executes the raw -> processed pipeline for CPCB AQI data.
    Saves cleaned data and station statistics to output_dir.
    """
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_df, file_report = load_all_cpcb_excel_files(raw_dir)
    if not raw_df.empty:
        cleaned_df, outliers, stats = clean_aqi_dataset(raw_df)
        cleaned_path = output_dir / "citypulse_cleaned_data.csv"
        cleaned_df.to_csv(cleaned_path, index=False)
        cleaned_parquet = output_dir / "citypulse_cleaned_data.parquet"
        cleaned_df.to_parquet(cleaned_parquet, index=False)
        logging.info(f"Saved {len(cleaned_df)} cleaned records to {cleaned_path}")

        stats_path = output_dir / "citypulse_station_summary.csv"
        stats.to_csv(stats_path)
        logging.info(f"Saved station statistics to {stats_path}")
        return cleaned_df, stats
    else:
        logging.info(f"No CPCB Excel files found in {raw_dir}. Checking processed repository archives...")
        hourly_path = output_dir / "mumbai_aqi_hourly_clean.parquet"
        if hourly_path.exists():
            logging.info(f"Repository processed hourly dataset available at {hourly_path}.")
        return pd.DataFrame(), pd.DataFrame()

if __name__ == "__main__":
    run_pipeline()

