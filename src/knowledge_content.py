"""Static content for the Action Centre and FAQ Knowledge Hub.

No external API, no chatbot, no network access. Everything here is plain Python data.

Integrity rules followed in this file:
  * Tiers are heuristic PM2.5 categories, not probabilities and not the official overall AQI.
  * Persistence ("tomorrow = today") is the operational baseline.
  * Responsible roles are illustrative; each city/ward has its own procedures.
  * Only two external references are listed, both official bodies. Verify links before citing.
"""

TIERS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]

NO_REF = "No external reference. Project judgement for human review."

REFERENCES = {
    "cpcb": {
        "name": "Central Pollution Control Board (CPCB), National Air Quality Index",
        "url": "https://cpcb.nic.in/",
        "note": "Official source for Indian AQI categories and monitoring data. "
                "CityPulse tiers use PM2.5 concentration bands only, not the full AQI calculation.",
    },
    "who": {
        "name": "WHO global air quality guidelines (2021)",
        "url": "https://www.who.int/publications/i/item/9789240034228",
        "note": "Background on PM2.5 and health. Not used to set CityPulse tiers.",
    },
}

# Each action: name, tiers it applies to, trigger, response, rationale, stakeholder, refs, limits.
ACTIONS = [
    {
        "name": "Routine monitoring",
        "tiers": ["Good", "Satisfactory"],
        "trigger": "Estimate and upper bound both stay in Good or Satisfactory.",
        "response": "Continue normal monitoring. Review the station again with the next data update.",
        "rationale": "Low estimated PM2.5 and a narrow band give no reason to divert resources.",
        "stakeholder": "Ward-level environment or monitoring cell",
        "refs": ["cpcb"],
        "limits": "Persistence cannot anticipate sudden changes. Check the data-quality warnings first.",
    },
    {
        "name": "Pre-position resources when the upper bound is worse than the estimate",
        "tiers": ["Satisfactory", "Moderate", "Poor", "Very Poor"],
        "trigger": "Upper end of the 80% range falls in a worse tier than the estimate.",
        "response": "Alert the response team that the station could worsen. Confirm inspection staff "
                    "and vehicles are available. No field action is needed yet.",
        "rationale": "The band shows plausible day-to-day change, so a worse tier at the upper bound is a "
                     "reason to prepare, not a prediction that it will happen.",
        "stakeholder": "Ward officer / zonal environment team",
        "refs": [],
        "limits": "About one in five outcomes is expected to fall outside the band. Coverage is weaker "
                  "when today's PM2.5 is already high.",
    },
    {
        "name": "Local dust, construction and burning source check",
        "tiers": ["Moderate", "Poor", "Very Poor", "Severe"],
        "trigger": "Estimate is Moderate or worse, or the upper bound reaches Moderate or worse.",
        "response": "Send staff to look at nearby construction sites, unpaved roads, waste or biomass burning, "
                    "and other visible local sources. Record what is observed.",
        "rationale": "Local sources are common contributors, and a site visit is a low-cost way to look.",
        "stakeholder": "Ward officer; construction and waste-management inspectors",
        "refs": [],
        "limits": "PM2.5 readings alone cannot identify a source. A site visit may find nothing, and "
                  "the cause may be regional or weather-driven.",
    },
    {
        "name": "Road dust control review",
        "tiers": ["Moderate", "Poor", "Very Poor", "Severe"],
        "trigger": "Moderate or worse, especially in dry weather.",
        "response": "Review whether road sweeping and water sprinkling are scheduled near the station.",
        "rationale": "Resuspended road dust adds to PM2.5 in dry conditions.",
        "stakeholder": "Roads / solid-waste management department",
        "refs": [],
        "limits": "Benefit near one station is uncertain. Not useful during rain.",
    },
    {
        "name": "Traffic management review",
        "tiers": ["Poor", "Very Poor", "Severe"],
        "trigger": "Poor or worse near a busy corridor.",
        "response": "Ask traffic authorities whether congestion at known choke points can be eased "
                    "for the period.",
        "rationale": "Congestion raises local vehicle emissions.",
        "stakeholder": "Traffic police; transport authority",
        "refs": [],
        "limits": "Traffic contribution is not measured by CityPulse. Treat as a prompt, not a finding.",
    },
    {
        "name": "Consider a public health advisory",
        "tiers": ["Poor", "Very Poor", "Severe"],
        "trigger": "Poor or worse estimate, confirmed by a second look at data quality.",
        "response": "Consider an advisory for sensitive groups (children, older adults, people with "
                    "heart or lung conditions). Wording should come from the health department.",
        "rationale": "Higher PM2.5 is associated with health effects, so people may want to limit exposure.",
        "stakeholder": "Public health department; communications cell",
        "refs": ["cpcb", "who"],
        "limits": "CityPulse is not an official warning system. An advisory needs official sign-off.",
    },
    {
        "name": "Verify the sensor before escalating",
        "tiers": TIERS,
        "trigger": "Few valid hours today, a sudden spike, a stale reading, or a station that is behind the others.",
        "response": "Check recent raw readings for stuck values or gaps. If the sensor looks faulty, "
                    "ask the station operator to confirm before acting on the estimate.",
        "rationale": "A daily value built from few hours or a faulty sensor can mislead the whole forecast.",
        "stakeholder": "Station operator (for example MPCB or IITM, as listed in the station name)",
        "refs": [],
        "limits": "Isolated spikes were kept in the data, not removed, so a spike may be real or a fault.",
    },
    {
        "name": "Escalate for emergency measures",
        "tiers": ["Very Poor", "Severe"],
        "trigger": "Very Poor or Severe estimate that survives the sensor check.",
        "response": "Escalate to the officer who decides on emergency measures and health advisories. "
                    "Provide the estimate, range, tier and data-quality notes.",
        "rationale": "Top-tier readings are the highest priority for a prioritisation tool.",
        "stakeholder": "Senior municipal officer / environment commissioner's office",
        "refs": ["cpcb"],
        "limits": "Decision authority sits with officials. The tool only supports prioritisation.",
    },
]


def actions_for_tier(tier):
    """Return the library entries that apply to a heuristic tier."""
    return [a for a in ACTIONS if tier in a["tiers"]]


FAQ = [
    {"category": "PM2.5 and AQI", "q": "What is PM2.5, and is it the same as AQI?",
     "a": "PM2.5 is the concentration of fine particles (under 2.5 micrometres) in the air, in ug/m3. "
          "AQI is an index that combines several pollutants into one category. CityPulse shows PM2.5 "
          "only, and its tiers are PM2.5 bands. They are not the official overall AQI."},
    {"category": "PM2.5 and AQI", "q": "What do the tiers mean?",
     "a": "Tiers are simple rule-based categories of the PM2.5 estimate: Good, Satisfactory, Moderate, "
          "Poor, Very Poor, Severe. They are heuristics. They are not probabilities of a bad day."},
    {"category": "Mumbai seasonal patterns", "q": "Does Mumbai's pollution change with the season?",
     "a": "In this dataset (2025 to 2026, four stations), PM2.5 was lowest in the monsoon and higher "
          "after the monsoon and in winter. Winter averages were roughly three times the monsoon "
          "averages. Only under two years of data are available, so treat this as a pattern in these "
          "stations, not a rule."},
    {"category": "Mumbai seasonal patterns", "q": "Why does a rainy day often look cleaner?",
     "a": "Rain tends to wash particles out of the air. The data shows low monsoon values, but "
          "CityPulse does not model weather, so it cannot say how much of the change is due to rain."},
    {"category": "Station prioritisation", "q": "How are stations ranked?",
     "a": "Stations are sorted by the estimated PM2.5 for the next day, with the upper end of the "
          "range used to break ties. The highest estimate is shown first. Ranking says where to look "
          "first, not what is wrong."},
    {"category": "Station prioritisation", "q": "Does a higher rank mean a pollution source was found?",
     "a": "No. PM2.5 alone cannot identify a source. A high rank is a prompt for a human check."},
    {"category": "Persistence forecasting", "q": "What is a persistence forecast?",
     "a": "It assumes tomorrow will look like today: the estimate for tomorrow is today's daily mean "
          "PM2.5. It is simple, easy to explain, and hard to beat for next-day values."},
    {"category": "Persistence forecasting", "q": "When will persistence be wrong?",
     "a": "When conditions change quickly, such as a rain event, a wind shift or a new local source. "
          "It cannot see these in advance."},
    {"category": "Uncertainty", "q": "How should I read the 80% range?",
     "a": "The range comes from how much PM2.5 changed from one day to the next in the past, at "
          "similar levels. About 8 in 10 past outcomes fell inside such ranges. It is a guide, not a "
          "guarantee, and it is weaker when PM2.5 is already high. See the Evidence panel for the "
          "measured numbers."},
    {"category": "Uncertainty", "q": "Why is the range wider at high pollution levels?",
     "a": "Day-to-day swings are larger when levels are high, and there are fewer past high days to "
          "learn from. Treat estimates at high levels with extra caution."},
    {"category": "Sensor faults and missing data", "q": "What if a station has missing readings?",
     "a": "A daily value uses only the valid hours available that day. Few valid hours make the value "
          "less reliable. The tool shows the number of hours used and warns when it is low."},
    {"category": "Sensor faults and missing data", "q": "How can I tell a faulty sensor from a real spike?",
     "a": "You cannot tell from the daily value alone. Look for repeated identical readings or sudden "
          "jumps, and ask the station operator. Isolated spikes were kept in the data, not removed."},
    {"category": "Recommended responses", "q": "Are the suggested actions orders?",
     "a": "No. They are advisory prompts for human review. Roles listed are illustrative, so check "
          "them against your own procedures."},
    {"category": "Recommended responses", "q": "Why does the action sometimes mention the upper bound?",
     "a": "If the upper end of the range reaches a worse tier, the tool suggests preparing resources, "
          "because the situation could worsen, even if it probably will not."},
    {"category": "Data freshness", "q": "Is this live data?",
     "a": "No. It is a stored snapshot built from files. The page shows the latest usable day and warns "
          "when the snapshot is more than two days old. There is no automatic live update."},
    {"category": "Data freshness", "q": "What does the forecast date mean?",
     "a": "The estimate is for the day after the latest observed day. It is a next-day estimate, not a "
          "forecast for several days."},
    {"category": "Four-station coverage", "q": "Can I use this for the whole city?",
     "a": "No. Only four stations are covered, and they do not represent every ward. Do not assume "
          "an unmonitored area is clean."},
    {"category": "Four-station coverage", "q": "Why only four stations?",
     "a": "These are the stations with usable data in the dataset used. More stations would give a "
          "better picture and are a natural next step."},
    {"category": "Why not machine learning", "q": "Why does CityPulse use persistence and not a machine-learning model?",
     "a": "A gradient-boosting model was tested on the same rows. In the broader walk-forward "
          "evaluation it did not beat the persistence baseline, so persistence stays as the operational "
          "baseline. The full comparison is in the evaluation report."},
    {"category": "Why not machine learning", "q": "Does that mean machine learning never helps?",
     "a": "No. It means that with four stations and under two years of data, it did not help for "
          "next-day values. More data, more stations or weather inputs might change this."},
]


def faq_categories():
    seen = []
    for item in FAQ:
        if item["category"] not in seen:
            seen.append(item["category"])
    return seen


def search_faq(query="", categories=None):
    """Case-insensitive keyword search over question, answer and category. All words must match."""
    words = [w for w in (query or "").lower().split() if w]
    cats = set(categories or [])
    out = []
    for item in FAQ:
        if cats and item["category"] not in cats:
            continue
        text = f"{item['q']} {item['a']} {item['category']}".lower()
        if all(w in text for w in words):
            out.append(item)
    return out
