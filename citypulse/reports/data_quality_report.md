# Data Quality & Coverage Audit Report — CityPulse: Mumbai

Audit Date: 2026-10-22 22:51:13  
Temporal Scope: 2021-01-01 to 2023-12-31  
Project Completeness Rule: >= 18 valid hours/day

---

## 1. Cleaning & Hygiene Summary Metrics

| Quality Diagnostic Metric | Value | Action Taken |
| :--- | :--- | :--- |
| **Total Hourly Rows Processed** | 601,560 | Ingested from CPCB CAAQMS archives |
| **Duplicate Timestamp Records** | 3,648 | Deduplicated on station x timestamp |
| **Negative Telemetry Values (< 0)** | 0 | Flagged (`flag_negative=1`), set to NaN |
| **Extreme Outliers (> 700 AQI)** | 0 | Flagged (`flag_extreme_outlier=1`), set to NaN |
| **Sensor-Stuck Episodes (>= 6h flatline)** | 7,056 | Flagged (`flag_sensor_stuck=1`), invalidated to NaN |
| **Short Gaps Interpolated (<= 2h)** | 13,333 | Linear interpolated (`flag_interpolated=1`); documented |
| **Total Daily Station Records** | 24,913 | Aggregated with completeness tracking |
| **Valid Daily Records (>= 18h)** | 22,608 (90.7%) | Retained for downstream modeling |

---

## 2. Station-Level Monitoring Reliability

Stations with valid day coverage >= 70% are selected for primary predictive modeling and longitudinal evaluation. Stations with low coverage (< 50%) are flagged for municipal monitoring expansion.

| Monitoring Station | Zone | Environmental Type | Total Days | Valid CPCB Days | Valid % | Mean AQI | Unhealthy Days (>200) | Modeling Tier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Airport T2** | Western Suburbs | Aviation Corridor | 1,077 | 1,040 | 96.6% | 121.6 | 114 | `Primary Modeling` |
| **Byculla Mumbai BMC** | MMR | Urban | 53 | 51 | 96.2% | 142.8 | 8 | `Primary Modeling` |
| **Malad West** | Western Suburbs | Commercial Tech Hub | 973 | 935 | 96.1% | 122.3 | 124 | `Primary Modeling` |
| **Borivali East IITM** | Western Suburbs | Near National Park | 881 | 845 | 95.9% | 114.2 | 72 | `Primary Modeling` |
| **Tondare-Taloja Navi Mumbai MPCB** | MMR | Urban | 160 | 153 | 95.6% | 112.0 | 17 | `Primary Modeling` |
| **Sion** | Central Mumbai | Highway Traffic Junction | 1,085 | 1,036 | 95.5% | 118.8 | 168 | `Primary Modeling` |
| **Sewri Mumbai BMC** | MMR | Urban | 42 | 40 | 95.2% | 182.7 | 12 | `Primary Modeling` |
| **Borivali East** | Western Suburbs | Near National Park | 1,060 | 1,004 | 94.7% | 88.6 | 54 | `Primary Modeling` |
| **Kandivali East** | Western Suburbs | Western Express Highway | 1,003 | 949 | 94.6% | 109.4 | 94 | `Primary Modeling` |
| **Powai** | Eastern Suburbs | Lake / Institutional | 1,073 | 1,014 | 94.5% | 103.5 | 93 | `Primary Modeling` |
| **Nerul Navi Mumbai** | Navi Mumbai | Planned Residential | 1,063 | 999 | 94.0% | 146.8 | 315 | `Primary Modeling` |
| **Mazgaon** | South Mumbai | Port / Maritime Docks | 1,056 | 984 | 93.2% | 153.0 | 305 | `Primary Modeling` |
| **Kherwadi Bandra East Mumbai MPCB** | MMR | Urban | 188 | 175 | 93.1% | 90.1 | 17 | `Primary Modeling` |
| **Vile Parle West** | Western Suburbs | Suburban Residential | 1,066 | 989 | 92.8% | 131.7 | 170 | `Primary Modeling` |
| **Sector-2E Kalamboli Navi Mumbai MPCB** | MMR | Urban | 162 | 150 | 92.6% | 129.0 | 38 | `Primary Modeling` |
| **Kurla** | Eastern Suburbs | Dense Urban Transit | 1,061 | 978 | 92.2% | 141.7 | 204 | `Primary Modeling` |
| **Colaba** | South Mumbai | Coastal / Residential | 1,022 | 938 | 91.8% | 102.1 | 57 | `Primary Modeling` |
| **Deonar** | Eastern Suburbs | Dumping Ground / Solid Waste | 908 | 829 | 91.3% | 146.2 | 229 | `Primary Modeling` |
| **Malad Mindspace** | Western Suburbs | Commercial Tech Hub | 161 | 147 | 91.3% | 86.0 | 4 | `Primary Modeling` |
| **Colaba Navy Nagar** | South Mumbai | Coastal Military / Green | 856 | 769 | 89.8% | 144.8 | 214 | `Primary Modeling` |
| **Shivaji Nagar Mumbai BMC** | MMR | Urban | 49 | 44 | 89.8% | 210.3 | 27 | `Primary Modeling` |
| **Kopripada-Vashi Navi Mumbai MPCB** | MMR | Urban | 198 | 177 | 89.4% | 112.6 | 32 | `Primary Modeling` |
| **Mulund West** | Eastern Suburbs | Foothill Suburban | 1,055 | 942 | 89.3% | 116.2 | 109 | `Primary Modeling` |
| **Chembur** | Eastern Suburbs | Industrial Corridor | 194 | 173 | 89.2% | 92.4 | 18 | `Primary Modeling` |
| **Worli Siddharth Nagar** | South Mumbai | Coastal Commercial | 927 | 823 | 88.8% | 102.9 | 31 | `Primary Modeling` |
| **Worli** | South Mumbai | Coastal Commercial | 1,034 | 916 | 88.6% | 108.0 | 76 | `Primary Modeling` |
| **Andheri East Chakala** | Western Suburbs | MIDC Industrial Belt | 996 | 880 | 88.4% | 136.1 | 209 | `Primary Modeling` |
| **Bandra Kurla Complex** | Western Suburbs | Commercial / Financial | 1,047 | 919 | 87.8% | 143.4 | 250 | `Primary Modeling` |
| **Mahape Navi Mumbai** | Navi Mumbai | TTC Industrial Zone | 1,061 | 931 | 87.7% | 131.5 | 149 | `Primary Modeling` |
| **Ghatkopar Mumbai BMC** | MMR | Urban | 39 | 34 | 87.2% | 142.0 | 3 | `Primary Modeling` |
| **Bhandup West** | Eastern Suburbs | Industrial / Residential | 874 | 760 | 87.0% | 114.3 | 64 | `Primary Modeling` |
| **Nerul Sec 19A** | Navi Mumbai | Planned Residential | 941 | 805 | 85.5% | 141.7 | 160 | `Primary Modeling` |
| **Kandivali West Mumbai BMC** | MMR | Urban | 48 | 41 | 85.4% | 173.6 | 8 | `Primary Modeling` |
| **Sanpada Navi Mumbai MPCB** | MMR | Urban | 177 | 151 | 85.3% | 98.4 | 23 | `Primary Modeling` |
| **Vasai West** | Palghar / MMR North | Outer MMR Coastal | 1,000 | 835 | 83.5% | 105.5 | 46 | `Primary Modeling` |
| **Bandra** | Western Suburbs | Suburban Mixed | 323 | 152 | 47.1% | 116.2 | 4 | `Coverage Gap` |

---

## 3. Data Integrity & Reproducibility Guarantees
1. **Zero Silent Drops:** Every suspicious record is assigned an explicit boolean flag column (`flag_negative`, `flag_sensor_stuck`, `flag_extreme_outlier`, `flag_interpolated`).
2. **Explicit Timezone:** All operational decisions and timestamps are tracked in Indian Standard Time (IST, UTC+05:30) with explicit UTC offset column.
3. **No Target Leakage:** Daily aggregation uses only measurements logged strictly up to 23:59 IST of that calendar date.
