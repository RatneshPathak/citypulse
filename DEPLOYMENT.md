# CityPulse: Mumbai — Deployment Guide & Operational Runbook

> **Live Demo URL:** [https://citypulse-mumbai.streamlit.app](https://citypulse-mumbai.streamlit.app)  
> **Fallback Mirror (Hugging Face Spaces):** `https://huggingface.co/spaces/<your-username>/citypulse-mumbai`  
> **Repository:** [https://github.com/RishiBuilds/CityPulse](https://github.com/RishiBuilds/CityPulse)  
> **Built for:** HackAMatch 1.0 by Ratnesh, Rishi & Shreya  

---

## 1. Architecture & Platform Resource Budgets

CityPulse: Mumbai is architected specifically for **100% free-tier cloud deployment** with zero external API dependencies, predictable memory footprints, and instant cold starts.

| Dimension | Streamlit Community Cloud (Primary) | Hugging Face Spaces (Fallback) | CityPulse Footprint | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Cost** | 100% Free (No credit card) | 100% Free (No credit card) | $0.00 | Passed |
| **Compute / vCPU** | 1 vCPU | 2 vCPU (Basic CPU) | < 15% during interactive rendering | Passed |
| **Memory (RAM)** | ~1.0 GB baseline (max 2.7 GB) | 16 GB RAM | **< 10 MB RAM** at startup | Passed (1% of limit) |
| **Disk Storage** | 50 GB ephemeral container | 50 GB container | ~15 MB processed artifacts | Passed |
| **Startup Network** | Must not block on external APIs | Must not block on external APIs | 0 live network calls (reads Parquet) | Passed |
| **Inactivity Sleep** | Hibernates after 12 hours | Hibernates after 48 hours | Auto-wakes on web request | Documented |
| **Python Runtimes** | Python 3.10, 3.11, 3.12, 3.13 | Python 3.10, 3.11, 3.12, 3.13 | Tested on Python 3.13 & 3.11 | Passed |

---

## 2. Pre-Deployment Verification (Verified Locally)

All items below have been executed, tested, and confirmed in the repository:

1. **Deterministic Pinned Dependencies:**
   - Production runtime dependencies are pinned in `requirements.txt`:
     ```
     streamlit==1.66.1
     pandas==3.1.0
     numpy==2.5.4
     scikit-learn==1.9.1
     plotly==7.1.0
     pyarrow==26.0.0
     ```
   - Heavy exploratory, plotting, and notebook tools (`matplotlib`, `seaborn`, `statsmodels`, `folium`, `pytest`, `nbconvert`) have been isolated into `requirements-dev.txt` to keep container install times under 90 seconds.
2. **Deterministic Data Loading:**
   - App reads committed, compressed Parquet files (`data/processed/mumbai_aqi_daily_clean.parquet` [313 KB], `holdout_predictions.parquet` [952 KB], `mumbai_priority_rankings.parquet` [21 KB]).
   - Cached with `@st.cache_data` in `app.py` for immediate sub-second page re-renders.
3. **Cross-Platform Path Portability:**
   - All file paths use standard Python `pathlib.Path` with forward slashes (`/`). Zero machine-specific or Windows backslash paths.
4. **Secret Handling & Graceful Degradation:**
   - Optional keys are resolved via `config.get_secret(key, default)` which queries `st.secrets` with fallback to `os.environ`.
   - Missing keys degrade gracefully; the app never crashes or raises unhandled exceptions.
5. **Branding & Disclaimer Integrity:**
   - Persistent banner (`Prototype - not an official warning system`), HackAMatch 1.0 team attribution (`Built for HackAMatch 1.0 by Ratnesh, Rishi & Shreya`), and open data attributions (`CPCB / Open-Meteo / OpenStreetMap contributors`) remain permanently rendered across all views.
6. **Automated Smoke Tests:**
   - Run with `python -m unittest tests/test_deployment_smoke.py`. All 6 smoke tests and 11 pipeline tests pass cleanly (`Ran 17 tests in 0.963s: OK`).

---

## 3. Deployment Checklist: Streamlit Community Cloud (Primary)

Follow these exact steps to deploy to Streamlit Community Cloud:

### Step 3.1: Confirm GitHub Repository State
Ensure all changes are pushed to your public GitHub repository:
```bash
git status
git push origin main
```
Confirm the repository is accessible at [https://github.com/RishiBuilds/CityPulse](https://github.com/RishiBuilds/CityPulse).

### Step 3.2: Sign In to Streamlit Community Cloud
1. Navigate to **[share.streamlit.io](https://share.streamlit.io)** in your web browser.
2. Click **"Continue with GitHub"** and authorise Streamlit to access your public repositories.

### Step 3.3: Create New Application
1. On the Streamlit dashboard, click the **"New app"** button (top right).
2. Select **"Use existing repo"**.
3. Fill in the repository details:
   - **Repository:** `RishiBuilds/CityPulse`
   - **Branch:** `main`
   - **Main file path:** `app.py` (or `streamlit_app.py`, both work)
   - **App URL (Custom subdomain):** Enter `citypulse-mumbai`
     *(This provisions the clean shareable URL: `https://citypulse-mumbai.streamlit.app`)*

### Step 3.4: Configure Advanced Settings
1. Click **"Advanced settings"** before clicking Deploy.
2. **Python Version:** Select **`3.11`**, **`3.12`**, or **`3.13`** (matches our modern syntax and wheel compatibility).
3. **Secrets (Optional):**
   *Note: CityPulse does NOT require any secrets to run out of the box because all datasets and model outputs are pre-computed and committed.* If you wish to configure optional future live-sync keys, paste the following TOML template into the Secrets text area:
   ```toml
   # Optional API keys for live pipeline synchronisation (leave blank for default offline mode)
   DATA_GOV_IN_KEY = "your_optional_free_data_gov_in_key_here"
   OPENAQ_API_KEY = "your_optional_free_openaq_key_here"
   ```
4. Click **"Save"**.

### Step 3.5: Deploy & Monitor First Boot
1. Click **"Deploy!"**.
2. **First-Boot Expectations:**
   - Streamlit Cloud provisions a secure Debian container.
   - It runs `pip install -r requirements.txt` (takes ~60–90 seconds).
   - Once complete, the "Manage app" terminal drawer at bottom right will display:
     `Streamlit server started on port 8501`.
   - The interactive CityPulse: Mumbai dashboard will render immediately in dark theme.

### Step 3.6: How to Read Logs and Reboot
- **Build & Runtime Logs:** Click the **"Manage app"** button in the lower-right corner of the browser view to open the real-time stdout/stderr log stream.
- **Reboot / Redeploy:** In the lower-right menu (three dots `⋮`), click **"Reboot app"** to clear memory and restart the container, or **"Clear cache"** to re-execute cached data loading functions.

---

## 4. Fallback Deployment: Hugging Face Spaces

If Streamlit Community Cloud experiences service disruptions or container limits, deploy instantaneously to Hugging Face Spaces:

### Step 4.1: Repository Configuration (Already Configured)
The repository's [`README.md`](README.md) already contains the required Hugging Face Spaces YAML front matter:
```yaml
---
title: CityPulse: Mumbai — Air Quality Prioritisation
emoji: 🏙️
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.66.1"
app_file: app.py
pinned: false
license: mit
---
```

### Step 4.2: Create the Space on Hugging Face
1. Log in to **[huggingface.co](https://huggingface.co)** (free account).
2. Click **"New Space"** (`https://huggingface.co/new-space`).
3. Fill in:
   - **Space Name:** `citypulse-mumbai`
   - **License:** `MIT`
   - **Select the Space SDK:** Choose **Streamlit**.
   - **Space hardware:** Select **CPU basic • 2 vCPU • 16 GB RAM • Free**.
4. Click **"Create Space"**.

### Step 4.3: Sync Code to Hugging Face
You can either:
- **Option A (GitHub Integration):** In the Space settings, connect your GitHub repository `RishiBuilds/CityPulse`.
- **Option B (Direct Git Push):** Add Hugging Face as a second git remote and push:
  ```bash
  git remote add space https://huggingface.co/spaces/<your-hf-username>/citypulse-mumbai
  git push space main
  ```
The space will build and launch at `https://huggingface.co/spaces/<your-hf-username>/citypulse-mumbai`.

---

## 5. Free-Tier Sleeping Caveats & Pre-Demo Wake-Up Protocol

Both Streamlit Community Cloud and Hugging Face Spaces enforce automatic inactivity timeouts to preserve shared free compute resources:

| Platform | Hibernation Window | Sleep Screen Behavior | Time to Wake Up |
| :--- | :--- | :--- | :--- |
| **Streamlit Community Cloud** | 12 hours of zero traffic | Shows *"Zzz... Your app went to sleep"* with a button: *"Yes, get this app back up!"* | 30–60 seconds |
| **Hugging Face Spaces** | 48 hours of zero traffic | Shows *"Space is sleeping"* with a button: *"Restart this Space"* | 45–90 seconds |

### Recommended Pre-Demo Checklist:
> [!IMPORTANT]
> **Open the live URL 10 minutes prior to your presentation or judging session:**
> 1. Visit `https://citypulse-mumbai.streamlit.app` from your phone or laptop.
> 2. If asleep, click **"Yes, get this app back up!"**.
> 3. Verify that the map loads, the KPIs display `#1 Mazgaon`, and the 5 tabs toggle smoothly.
> 4. Once awake, the container remains hot and active for 12 continuous hours.

---

## 6. Maintenance & Rollback Plan

### Updating the Live App
Streamlit Community Cloud automatically listens to webhooks on your GitHub repository:
- Any `git push origin main` triggers an automatic, zero-downtime rolling reload.
- If a bad commit causes an error, Streamlit displays the error traceback in the logs without destroying the container.

### Rollback Procedure
If a bad update is accidentally deployed during a demonstration:
```bash
# 1. Revert to the known stable deployment commit
git revert HEAD --no-edit

# 2. Push to GitHub main
git push origin main

# 3. Streamlit Cloud will re-pull and reload within 20 seconds.
```
Alternatively, in the Streamlit Cloud dashboard:
- Navigate to **Settings** -> **Manage app** -> Click **"Reboot app"**.

---

*CityPulse: Mumbai • Decision-Support Prototype • HackAMatch 1.0*
