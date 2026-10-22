# CityPulse: Mumbai — 3-Minute Live Demo Script

**For: HackAMatch 1.0 Final Presentation**  
**Presenters: Ratnesh, Rishi & Shreya**  
**Timing: 3 minutes (180 seconds)**

---

## 🎯 Opening Hook (15 seconds)

> "Mumbai has 36 air quality monitoring stations across the city. When pollution spikes, municipal environmental officers have maybe 5-10 inspection teams. **Which zones do they inspect THIS WEEK?**
> 
> That's the decision CityPulse answers — using 100% free, open data."

**Action:** Show app homepage, point to "5 inspection teams for 36 zones" in sidebar.

---

## 📊 Tab 1: The Priority Rankings (30 seconds)

> "Tab 1 shows today's priority leaderboard. This is a **multi-criteria score**: recent exposure, persistence above thresholds, trend acceleration, forecast risk, and vulnerability context.
> 
> **Bandra Kurla Complex ranks #1** with a score of 87.4. Why? Because..."

**Action:** Click on Tab 1 → Point to Score Breakdown chart.

> "...it has high recent exposure (red), 5 days above 150 AQI (orange), and a worsening trend (yellow). The forecast puts it at 70% probability of unhealthy air tomorrow."

**Action:** Scroll to Action Dossier.

> "The system recommends: deploy mobile anti-smog mist cannons along the highway corridor during morning peak. **Notice the caveats** — we don't claim this is THE cause, just a likely contributor."

---

## 🎛️ Tab 2: What-If Policy Simulator (30 seconds)

> "Now suppose policy changes. Maybe the officer wants to prioritize **forecast risk over past exposure**."

**Action:** Switch to Tab 2 → Adjust sidebar weights (increase Forecast Risk to 0.40, decrease Exposure to 0.20).

> "Watch the ranks update. **Mazgaon jumps from #4 to #2.** The rank movement chart shows arrows — green means improved priority, red means dropped.
> 
> But which zones are **stable** across policy choices? Click Run Stability Simulation..."

**Action:** Click "Run Stability Simulation" → Wait 10 seconds → Show probability heatmap.

> "500 random weight combinations. **Worli has 92% probability of staying in the top 5.** Robust to policy. **Goregaon only 34%** — volatile, depends on weights you choose."

---

## 🗺️ Tab 3: Inspection Route (20 seconds)

> "Tab 3: Route Planner. Given the top-5, what's the most efficient visiting order?"

**Action:** Switch to Tab 3 → Click "Compute Optimal Route."

> "Nearest-neighbor tour: start at Worli, visit 5 zones, **total 18.3 km** straight-line. The map shows numbered stops. **We're honest:** this is NOT road routing — just a heuristic. Real travel will be longer."

---

## ✅ Tab 8: Honest Validation (25 seconds)

> "Now the validation judges want to see: **does it actually work?**
> 
> Tab 8: We backtested this strategy on the entire 2023 holdout. Simulated weekly inspections."

**Action:** Switch to Tab 8 → Point to backtest metrics.

> "**Priority strategy hit rate: 42.3%.** Random selection: 31.8%. That's **+33% lift** — concentrating resources on zones that actually had elevated AQI.
> 
> **But we're honest:** the forecast model doesn't beat persistence on MAE. Persistence is 19.4, model is 20.3. Air quality is highly autoregressive — beating yesterday is hard.
> 
> The 80% prediction intervals? They undercover at 74%. **We show you where it doesn't work.**"

---

## 📄 Tab 4: Printable Briefing (15 seconds)

> "Tab 4: The field officer needs something tangible. One click, download a printable weekly briefing."

**Action:** Switch to Tab 4 → Click "Download HTML."

> "Top-5 zones, recommended actions, evidence, data attribution. This is the artifact they carry to the inspection site. PDF too, if you have the library."

---

## 🏘️ Tab 9: Citizen Mode (15 seconds)

> "Not just for officials. Tab 9: **Citizen View.** Simplified, plain-language health guidance."

**Action:** Switch to Tab 9 → Show AQI card.

> "Current AQI is 147 — Moderate. Health guidance: sensitive groups should limit outdoor exertion. No medical claims, just CPCB official categories. You can download a shareable card for WhatsApp or Twitter."

---

## 🎬 Tab 10: Guided Demo (10 seconds)

> "Tab 10 is actually a guided demo mode. 8 steps, auto-advance option. **You could run this on stage with zero narration** — it walks through the whole story. Problem, data, solution, validation, impact."

**Action:** Switch to Tab 10 → Show step 1.

> "Perfect for automated kiosks or investor pitches."

---

## 🎯 Closing: Impact & Next Steps (20 seconds)

> "**Impact, computed from the data**: The top-5 zones account for 58% of all high-AQI station-days in 2023. Concentrating finite resources there is measurably efficient.
> 
> **Next steps:**
> - Live CPCB API integration (no more historical replay)
> - Satellite AOD data to finally beat persistence
> - SMS alerts for citizens: 'AQI forecast 180+ tomorrow, limit outdoor activity'
> - Multi-city: Delhi, Pune, Kolkata, Bengaluru
> 
> **All code is MIT-licensed, open-source.** Zero paid APIs. Every number you saw is computed from verifiable CPCB and Open-Meteo data.
> 
> **CityPulse: Predict. Explain. Act.** Thank you."

---

## ⏱️ Timing Breakdown

| Section | Seconds | Cumulative |
|---------|---------|------------|
| Opening Hook | 15 | 0:15 |
| Tab 1: Priority Rankings | 30 | 0:45 |
| Tab 2: What-If Simulator | 30 | 1:15 |
| Tab 3: Route Planner | 20 | 1:35 |
| Tab 8: Validation | 25 | 2:00 |
| Tab 4: Briefing | 15 | 2:15 |
| Tab 9: Citizen Mode | 15 | 2:30 |
| Tab 10: Guided Demo | 10 | 2:40 |
| Closing | 20 | 3:00 |

**Total: 180 seconds (3 minutes)**

---

## 🎤 Speaker Notes

**For Ratnesh (Technical Deep-Dive):**
- Emphasize backtest methodology (chronological holdout, no leakage)
- Explain rank stability Monte Carlo (500 runs, ±30% perturbation)
- Highlight honest validation: "We show where it doesn't work"

**For Rishi (Product & UX):**
- Emphasize "finite resources" framing (5 teams, 36 zones)
- Show route planner practical use case
- Highlight citizen mode simplification

**For Shreya (Data & Impact):**
- Emphasize 100% free data (no API keys, no credit cards)
- Computed impact: "top-5 account for 58% of high-AQI days"
- Future work: live integration, SMS alerts

---

## 🧪 Backup Slides (If Demo Fails)

1. **Screenshot: Priority Rankings** (Tab 1 with Bandra #1)
2. **Screenshot: What-If Simulator** (rank movement chart with arrows)
3. **Screenshot: Route Map** (5 stops with route line)
4. **Screenshot: Validation Panel** (backtest metrics showing +33% lift)
5. **Screenshot: Citizen View** (AQI card with health guidance)

---

## 🔥 Spicy One-Liners for Judges

**Technical Judges:**
> "We ran 500 Monte Carlo simulations to find which zones are robust to policy changes. That's in Tab 2."

**Product Judges:**
> "The field officer downloads a one-page briefing in Tab 4. That's what they carry to the inspection site."

**Design Judges:**
> "Dark theme, Material Symbols icons, color-blind-safe palettes. WCAG AA compliant. Zero emojis."

**Impact Judges:**
> "Top-5 zones account for 58% of high-AQI station-days. Concentrating resources there is measurably efficient."

---

**Last Rehearsal:** October 22, 2026, 11:45 PM  
**Demo URL:** https://citypulse-mumbai.streamlit.app  
**Fallback:** `streamlit run app.py` from local clone
