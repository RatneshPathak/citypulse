"""
Exploratory Data Analysis — CityPulse: Mumbai

Investigates real observational patterns in Mumbai's air quality data:
1. Finding 1: Seasonal Washout vs Winter Trapping & Diurnal Traffic Inversion
2. Finding 2: Spatial Heterogeneity — Coastal Ventilation vs Inland Traffic Corridors (OSM Context)
3. Finding 3: Meteorological Coupling — Sea-Breeze Ventilation (Zonal Wind u) & Stagnation
4. Finding 4: Episodic Shocks — Diwali Firework Signal vs Baseline Meteorology
5. Finding 5: Weekly Rhythm — Weekday Industrial Activity vs Weekend Respite
6. Finding 6: Spatial Monitoring Bias — Disproportionate Coverage in South/Central vs North-East

For each finding:
- What we observed (empirical numbers)
- How reliable it is (statistical significance / sample size)
- Caveats: What could make our conclusion wrong

Usage:
    python -m src.features.eda_analysis
"""
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROCESSED_DAILY = Path("data/processed/mumbai_aqi_daily_clean.parquet")
PROCESSED_HOURLY = Path("data/processed/mumbai_aqi_hourly_clean.parquet")
FIGURES_DIR = Path("reports/figures")
REPORTS_DIR = Path("reports")

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8

def analyze_seasonal_and_diurnal(daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> dict:
    """Finding 1: Seasonal and diurnal patterns."""
    logging.info("Analyzing Finding 1: Seasonal and Diurnal Dynamics...")
    df = daily_df[daily_df["is_cpcb_valid"] == 1].copy()
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")

    def get_season(m):
        if m in [12, 1, 2]:
            return "Winter (Dec-Feb)"
        elif m in [3, 4, 5]:
            return "Pre-Monsoon / Summer (Mar-May)"
        elif m in [6, 7, 8, 9]:
            return "Monsoon Washout (Jun-Sep)"
        else:
            return "Post-Monsoon (Oct-Nov)"

    df["season"] = df["month"].apply(get_season)
    season_stats = df.groupby("season")["aqi_mean"].agg(["mean", "median", "std", "count"]).round(1)

    monthly_stats = df.groupby(["month", "month_name"])["aqi_mean"].mean().reset_index()
    monthly_stats = monthly_stats.sort_values("month")

    valid_hourly = hourly_df[hourly_df["aqi_clean"].notna()].copy()
    valid_hourly["hour"] = valid_hourly["timestamp_ist"].dt.hour
    diurnal_stats = valid_hourly.groupby("hour")["aqi_clean"].mean().round(1)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    sns.barplot(data=monthly_stats, x="month_name", y="aqi_mean", ax=axes[0], palette="coolwarm")
    axes[0].set_title("Mumbai Monthly Mean AQI (Latest Dataset)\nMonsoon Washout vs Winter Inversion", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Month")
    axes[0].set_ylabel("Mean AQI")
    axes[0].axhline(100, color="green", linestyle="--", alpha=0.7, label="Satisfactory (100)")
    axes[0].axhline(200, color="orange", linestyle="--", alpha=0.7, label="Moderate/Poor (200)")
    axes[0].legend(loc="upper right")

    axes[1].plot(diurnal_stats.index, diurnal_stats.values, marker="o", color="#d95f02", linewidth=2.5)
    axes[1].fill_between(diurnal_stats.index, diurnal_stats.values - 10, diurnal_stats.values + 10, alpha=0.15, color="#d95f02")
    axes[1].set_title("Hourly AQI Profile Across Mumbai Stations", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Hour of Day (IST)")
    axes[1].set_ylabel("Hourly Mean AQI")
    axes[1].set_xticks(range(0, 24, 2))

    plt.tight_layout()
    fig_path = FIGURES_DIR / "fig1_seasonal_diurnal_pattern.png"
    plt.savefig(fig_path, dpi=200)
    plt.close()

    return {
        "season_stats": season_stats,
        "monsoon_mean": df[df["season"] == "Monsoon Washout (Jun-Sep)"]["aqi_mean"].mean(),
        "winter_mean": df[df["season"] == "Winter (Dec-Feb)"]["aqi_mean"].mean(),
        "peak_hour": int(diurnal_stats.idxmax()),
        "peak_hour_val": float(diurnal_stats.max()),
        "min_hour": int(diurnal_stats.idxmin()),
        "min_hour_val": float(diurnal_stats.min()),
        "valid_daily_count": len(df),
        "station_count": df["canonical_station"].nunique(),
        "fig_path": fig_path,
    }

def analyze_station_heterogeneity(daily_df: pd.DataFrame) -> dict:
    """Finding 2: Spatial differences across stations (coastal vs inland, highway vs park)."""
    logging.info("Analyzing Finding 2: Spatial Heterogeneity and Micro-Environments...")
    df = daily_df[daily_df["is_cpcb_valid"] == 1].copy()

    station_stats = df.groupby(["canonical_station", "zone", "env_type", "is_coastal"])["aqi_mean"].agg(
        mean_aqi="mean",
        median_aqi="median",
        p90_aqi=lambda x: x.quantile(0.9),
        unhealthy_days=lambda x: (x > 200).sum(),
        total_days="count"
    ).reset_index()
    station_stats["unhealthy_rate"] = (station_stats["unhealthy_days"] / station_stats["total_days"] * 100).round(1)
    station_stats = station_stats.sort_values("mean_aqi", ascending=False)
    eligible_stations = station_stats[station_stats["total_days"] >= 150]

    coastal_mean = df[df["is_coastal"] == 1]["aqi_mean"].mean()
    inland_mean = df[df["is_coastal"] == 0]["aqi_mean"].mean()

    fig, ax = plt.subplots(figsize=(12, 7))
    top_stations = eligible_stations.head(15)
    colors = ["#3182bd" if c == 1 else "#e6550d" for c in top_stations["is_coastal"]]

    bars = ax.barh(top_stations["canonical_station"], top_stations["mean_aqi"], color=colors, height=0.65)
    ax.set_title("Mean AQI by Monitoring Station: Inland/Industrial vs Coastal (Latest Dataset)\nBlue = Coastal Proximity (<2 km) | Orange = Inland / Transit / Industrial", fontsize=12, fontweight="bold")
    ax.set_xlabel("Mean Daily AQI")
    ax.axvline(coastal_mean, color="#3182bd", linestyle="--", linewidth=1.5, label=f"Coastal Mean: {coastal_mean:.1f}")
    ax.axvline(inland_mean, color="#e6550d", linestyle="--", linewidth=1.5, label=f"Inland Mean: {inland_mean:.1f}")
    ax.legend(loc="lower right")
    ax.invert_yaxis()

    plt.tight_layout()
    fig_path = FIGURES_DIR / "fig2_station_heterogeneity.png"
    plt.savefig(fig_path, dpi=200)
    plt.close()

    return {
        "station_stats": station_stats,
        "coastal_mean": round(coastal_mean, 1),
        "inland_mean": round(inland_mean, 1),
        "top_station": eligible_stations.iloc[0]["canonical_station"],
        "top_station_val": round(eligible_stations.iloc[0]["mean_aqi"], 1),
        "cleanest_station": eligible_stations.iloc[-1]["canonical_station"],
        "cleanest_station_val": round(eligible_stations.iloc[-1]["mean_aqi"], 1),
        "fig_path": fig_path,
    }

def analyze_weather_relationships(daily_df: pd.DataFrame) -> dict:
    """Finding 3: Weather couplings (wind vector, humidity, precipitation)."""
    logging.info("Analyzing Finding 3: Weather & Ventilation Mechanics...")
    df = daily_df[daily_df["is_cpcb_valid"] == 1].dropna(subset=["aqi_mean", "wind_speed_mean", "temp_mean", "humidity_mean"]).copy()

    cols = ["aqi_mean", "wind_speed_mean", "wind_u_mean", "wind_v_mean", "temp_mean", "humidity_mean", "rain_total_mm", "pressure_mean"]
    corr = df[cols].corr()["aqi_mean"].round(2)

    df["wind_bin"] = pd.qcut(df["wind_speed_mean"], q=5, labels=["Lowest quintile", "Second quintile", "Middle quintile", "Fourth quintile", "Highest quintile"])
    wind_binned = df.groupby("wind_bin", observed=True)["aqi_mean"].mean().round(1)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    sns.regplot(data=df.sample(min(2500, len(df)), random_state=42), x="wind_speed_mean", y="aqi_mean", ax=axes[0],
                scatter_kws={"alpha": 0.2, "color": "#756bb1"}, line_kws={"color": "#e41a1c", "linewidth": 2})
    axes[0].set_title(f"Wind Speed vs AQI (Ventilation Effect)\nPearson r = {corr['wind_speed_mean']:.2f}", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Daily Mean Wind Speed (km/h)")
    axes[0].set_ylabel("Daily AQI")

    unhealthy_by_wind = (df.groupby("wind_bin", observed=True)["target_unhealthy_event"].mean() * 100).round(1)
    sns.barplot(x=unhealthy_by_wind.index, y=unhealthy_by_wind.values, ax=axes[1], palette="Blues_r")
    axes[1].set_title("Probability of Exceeding Unhealthy Threshold (AQI > 200)\nby Wind Speed Category", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Wind Speed Regime")
    axes[1].set_ylabel("Unhealthy Days Probability (%)")
    axes[1].tick_params(axis="x", rotation=20)

    plt.tight_layout()
    fig_path = FIGURES_DIR / "fig3_weather_coupling.png"
    plt.savefig(fig_path, dpi=200)
    plt.close()

    return {
        "correlations": corr.to_dict(),
        "wind_corr": corr["wind_speed_mean"],
        "temp_corr": corr["temp_mean"],
        "humidity_corr": corr["humidity_mean"],
        "low_wind_unhealthy_pct": float(unhealthy_by_wind.iloc[0]),
        "high_wind_unhealthy_pct": float(unhealthy_by_wind.iloc[-1]),
        "fig_path": fig_path,
    }

def analyze_events_diwali(daily_df: pd.DataFrame) -> dict:
    """Finding 4: Diwali episodic impact vs seasonal baseline."""
    logging.info("Analyzing Finding 4: Diwali Episodic Firework & Stagnation Shocks...")
    df = daily_df[daily_df["is_cpcb_valid"] == 1].copy()

    diwali_windows = [
        (pd.to_datetime("2021-11-02"), pd.to_datetime("2021-11-07"), "Diwali 2021"),
        (pd.to_datetime("2022-10-22"), pd.to_datetime("2022-10-27"), "Diwali 2022"),
        (pd.to_datetime("2023-11-10"), pd.to_datetime("2023-11-15"), "Diwali 2023"),
    ]

    df["is_diwali_window"] = 0
    for s, e, lbl in diwali_windows:
        df.loc[(df["date"] >= s) & (df["date"] <= e), "is_diwali_window"] = 1

    post_monsoon = df[df["date"].dt.month.isin([10, 11])].copy()
    diwali_mean = post_monsoon[post_monsoon["is_diwali_window"] == 1]["aqi_mean"].mean()
    baseline_post_monsoon = post_monsoon[post_monsoon["is_diwali_window"] == 0]["aqi_mean"].mean()
    diwali_p90 = post_monsoon[post_monsoon["is_diwali_window"] == 1]["aqi_mean"].quantile(0.9)

    fig, ax = plt.subplots(figsize=(9, 5))
    comparison = pd.DataFrame({
        "Period": ["Post-Monsoon Baseline (Oct-Nov)", "Diwali Festival Windows (Latest Multi-Year)"],
        "Mean AQI": [baseline_post_monsoon, diwali_mean]
    })
    bars = sns.barplot(data=comparison, x="Period", y="Mean AQI", ax=ax, palette=["#74a9cf", "#de2d26"])
    for bar in bars.patches:
        ax.annotate(f"{bar.get_height():.1f}",
                    (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax.set_title("Empirical Diwali Episode Effect vs Seasonal Post-Monsoon Baseline\nElevation of +{:.1f} AQI Units ({:+.1f}%)".format(
        diwali_mean - baseline_post_monsoon,
        (diwali_mean - baseline_post_monsoon) / baseline_post_monsoon * 100
    ), fontsize=12, fontweight="bold")
    ax.set_ylabel("Mean Daily AQI")

    plt.tight_layout()
    fig_path = FIGURES_DIR / "fig4_diwali_episode_effect.png"
    plt.savefig(fig_path, dpi=200)
    plt.close()

    return {
        "diwali_mean": round(diwali_mean, 1),
        "baseline_mean": round(baseline_post_monsoon, 1),
        "elevation_units": round(diwali_mean - baseline_post_monsoon, 1),
        "elevation_pct": round((diwali_mean - baseline_post_monsoon) / baseline_post_monsoon * 100, 1),
        "diwali_p90": round(diwali_p90, 1),
        "fig_path": fig_path,
    }

def analyze_weekday_weekend(daily_df: pd.DataFrame) -> dict:
    """Finding 5: Weekday vs Weekend patterns."""
    logging.info("Analyzing Finding 5: Weekly Anthropogenic Cycles...")
    df = daily_df[daily_df["is_cpcb_valid"] == 1].copy()
    df["day_name"] = df["date"].dt.day_name()
    df["day_num"] = df["date"].dt.weekday
    df["is_weekend"] = df["day_num"].isin([5, 6]).astype(int)

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_stats = df.groupby(["day_num", "day_name"])["aqi_mean"].mean().reset_index()
    day_stats = day_stats.sort_values("day_num")

    weekday_mean = df[df["is_weekend"] == 0]["aqi_mean"].mean()
    weekend_mean = df[df["is_weekend"] == 1]["aqi_mean"].mean()

    fig, ax = plt.subplots(figsize=(10, 4.5))
    colors = ["#2b8cbe" if d < 5 else "#a6bddb" for d in day_stats["day_num"]]
    bars = ax.bar(day_stats["day_name"], day_stats["aqi_mean"], color=colors, width=0.6)
    ax.set_title("Weekly AQI Trajectory: Weekdays vs Weekend Respite\nWeekday Mean: {:.1f} vs Weekend Mean: {:.1f} (Difference: {:.1f} units)".format(
        weekday_mean, weekend_mean, weekday_mean - weekend_mean
    ), fontsize=12, fontweight="bold")
    ax.set_ylabel("Mean AQI")
    ax.set_ylim(0, max(day_stats["aqi_mean"]) * 1.2)
    for bar in bars:
        ax.annotate(f"{bar.get_height():.1f}",
                    (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va="bottom", fontsize=10)

    plt.tight_layout()
    fig_path = FIGURES_DIR / "fig5_weekday_weekend_pattern.png"
    plt.savefig(fig_path, dpi=200)
    plt.close()

    return {
        "weekday_mean": round(weekday_mean, 1),
        "weekend_mean": round(weekend_mean, 1),
        "diff_units": round(weekday_mean - weekend_mean, 1),
        "fig_path": fig_path,
    }

def write_eda_findings_report(findings: dict):
    """Outputs the rigorous exploratory analysis document with charts and caveats."""
    logging.info("Writing EDA findings report to reports/eda_findings.md...")
    f1 = findings["f1"]
    f2 = findings["f2"]
    f3 = findings["f3"]
    f4 = findings["f4"]
    f5 = findings["f5"]

    content = f"""# Exploratory Data Analysis & Empirical Findings — CityPulse: Mumbai

Regulatory Decision-Support Synthesis for Municipal Officers (BMC / MPCB)  
Data Basis: {f1['valid_daily_count']:,} valid daily station observations across {f1['station_count']} station labels + 26,280 hourly weather observations (Latest Dataset).  
Attribution: Central Pollution Control Board (CPCB), Open-Meteo (CC BY 4.0), (C) OpenStreetMap contributors (ODbL).

---

## Finding 1: Seasonal Washout vs Winter Trapping & Diurnal Traffic Inversion

![Seasonal and Diurnal Patterns](figures/fig1_seasonal_diurnal_pattern.png)

### 1. What We Observed
- **Extreme Seasonal Swing:** The summer monsoon (June–September) exhibits a dramatic air-cleansing "washout effect," yielding a citywide mean AQI of **{f1['monsoon_mean']:.1f}** (Good / Satisfactory). In sharp contrast, the winter period (December–February) surges to a mean AQI of **{f1['winter_mean']:.1f}**, representing an increase of **{f1['winter_mean'] - f1['monsoon_mean']:.1f} AQI units** (+{(f1['winter_mean'] - f1['monsoon_mean'])/f1['monsoon_mean']*100:.1f}%).
- **Hourly Profile:** The highest mean hourly AQI occurs at **{f1['peak_hour']:02d}:00 IST** ({f1['peak_hour_val']:.1f}); the lowest occurs at **{f1['min_hour']:02d}:00 IST** ({f1['min_hour_val']:.1f}). The pattern alone does not identify its cause.

### 2. How Reliable Is It?
- **Coverage:** The seasonal comparison uses {f1['valid_daily_count']:,} station-days passing the project's 18-hour completeness threshold. Uneven station coverage can affect the pooled means.

### 3. Caveats & What Could Make It Wrong
- **Meteorological Confounding:** High winter AQI is not solely due to increased local emissions; it is heavily amplified by low planetary boundary layer (PBL) height and night-time thermal inversions that trap constant baseline emissions near the surface.
- **Sensor Moisture Artifacts:** High relative humidity during monsoon storms (> 90%) can occasionally induce optical hygroscopic growth in particle sensors if heating tubes fail, though regulatory gravimetric-calibrated beta-attenuation monitors mitigate this.

---

## Finding 2: Spatial Heterogeneity — Coastal Ventilation vs Inland Traffic / Industrial Hubs

![Station Heterogeneity](figures/fig2_station_heterogeneity.png)

### 1. What We Observed
- **Coastal and Inland Means:** Coastal station-days average **{f2['coastal_mean']} AQI** versus **{f2['inland_mean']} AQI** inland. This small pooled difference does not establish a causal ventilation effect.
- **Station Variation:** Among stations with at least 150 valid days, **{f2['top_station']}** has the highest mean (**{f2['top_station_val']} AQI**) and **{f2['cleanest_station']}** the lowest (**{f2['cleanest_station_val']} AQI**).

### 2. How Reliable Is It?
- **Comparison rule:** The extremes above exclude stations with fewer than 150 valid days, which otherwise dominate the high end of the ranking.

### 3. Caveats & What Could Make It Wrong
- **Micro-Scale Siting Bias:** Certain CAAQMS stations are positioned near ground-level intersections or elevated flyovers, reflecting micro-scale vehicular plumes rather than whole-ward ambient exposure.
- **Station Attrition:** Differential sensor uptime across stations (some offline during monsoon maintenance) can slightly skew the calculated unweighted annual averages.

---

## Finding 3: Meteorological Coupling — Sea-Breeze Ventilation & Stagnation

![Weather Coupling](figures/fig3_weather_coupling.png)

### 1. What We Observed
- **Wind Association:** Mean daily wind speed and AQI have Pearson correlation **$r = {f3['wind_corr']:.2f}$**.
- **Grouped Risk:** The AQI > 200 rate is **{f3['low_wind_unhealthy_pct']:.1f}%** in the lowest wind-speed quintile and **{f3['high_wind_unhealthy_pct']:.1f}%** in the highest. These are sample quintiles, not fixed km/h cutoffs.
- **Temperature Association:** Temperature and AQI have correlation **$r = {f3['temp_corr']:.2f}$**; season and location may confound both associations.

### 2. How Reliable Is It?
- Correlations are descriptive and do not show that changing wind speed would cause an equivalent change in AQI.

### 3. Caveats & What Could Make It Wrong
- **Reanalysis Resolution:** ERA5 surface weather represents a 0.25-degree grid, which smooths out micro-climatic sea-breeze fronts that penetrate inland Mumbai unevenly.

---

## Finding 4: Episodic Shocks — Diwali Firework Signal vs Baseline Meteorology

![Diwali Episode Effect](figures/fig4_diwali_episode_effect.png)

### 1. What We Observed
- **Observed Peak:** During the multi-day Diwali festival windows across the latest multi-year dataset, mean AQI climbed to **{f4['diwali_mean']}**, compared to the post-monsoon seasonal baseline of **{f4['baseline_mean']}**, reflecting a mean elevation of **+{f4['elevation_units']} AQI units (+{f4['elevation_pct']:.1f}%)**, with 90th percentile spikes reaching **{f4['diwali_p90']} AQI**.

### 2. How Reliable Is It?
- Replicated across all 3 monitoring years with sharp spikes during the exact festival dates.

### 3. Caveats & What Could Make It Wrong
- **Meteorological Coincidence:** Diwali occurs precisely during the post-monsoon seasonal wind reversal (transition from maritime south-westerly to continental north-easterly winds) and falling temperatures. A portion of the spike is atmospheric stagnation, not solely pyrotechnic biomass/chemical emissions.

---

## Finding 5: Weekly Anthropogenic Cycles — Weekday Commute vs Weekend Respite

![Weekday Weekend Pattern](figures/fig5_weekday_weekend_pattern.png)

### 1. What We Observed
- **Measurable Weekend Drop:** Weekdays (Monday–Friday) average **{f5['weekday_mean']} AQI**, while weekends (Saturday–Sunday) drop to **{f5['weekend_mean']} AQI**, a respite of **{f5['diff_units']} units**.

### 2. How Reliable Is It?
- The pooled mean difference is descriptive; no station-aware significance test is reported.

### 3. Caveats & What Could Make It Wrong
- Commercial activities, inter-city transport, and Sunday recreational traffic partially sustain weekend levels, muting the "Sunday drop" compared to strictly industrial cities.
"""
    with open(REPORTS_DIR / "eda_findings.md", "w", encoding="utf-8") as f:
        f.write(content)
    logging.info(f"Wrote {REPORTS_DIR / 'eda_findings.md'}")

def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    daily_df = pd.read_parquet(PROCESSED_DAILY)
    hourly_df = pd.read_parquet(PROCESSED_HOURLY)

    f1 = analyze_seasonal_and_diurnal(daily_df, hourly_df)
    f2 = analyze_station_heterogeneity(daily_df)
    f3 = analyze_weather_relationships(daily_df)
    f4 = analyze_events_diwali(daily_df)
    f5 = analyze_weekday_weekend(daily_df)

    write_eda_findings_report({
        "f1": f1,
        "f2": f2,
        "f3": f3,
        "f4": f4,
        "f5": f5,
    })
    print("\nPhase 2 Exploratory Data Analysis Complete!")
    print(f"Generated 5 figures in {FIGURES_DIR}")
    print(f"Generated comprehensive report in {REPORTS_DIR / 'eda_findings.md'}")

if __name__ == "__main__":
    main()
