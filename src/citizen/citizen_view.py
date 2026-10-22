"""
CityPulse: Mumbai — Citizen-Facing View

Simplified public view with plain-language health guidance and shareable AQI cards.
"""
from datetime import datetime
from typing import Dict, Tuple

import pandas as pd
import streamlit as st
from theme import get_aqi_category_color, COLORS


# CPCB Health Guidance by Category (Official Guidelines)
HEALTH_GUIDANCE = {
    "Good": {
        "general": "Air quality is satisfactory, and air pollution poses little or no risk.",
        "sensitive": "Enjoy normal outdoor activities.",
        "icon": ":material/sentiment_satisfied:",
        "color": "#2ECC71"
    },
    "Satisfactory": {
        "general": "Air quality is acceptable. However, there may be a risk for some people who are unusually sensitive to air pollution.",
        "sensitive": "Unusually sensitive people should consider limiting prolonged outdoor exertion.",
        "icon": ":material/sentiment_neutral:",
        "color": "#3498DB"
    },
    "Moderate": {
        "general": "Members of sensitive groups may experience health effects. The general public is less likely to be affected.",
        "sensitive": "People with respiratory disease (e.g., asthma), children, and older adults should limit prolonged outdoor exertion.",
        "icon": ":material/sentiment_worried:",
        "color": "#F5C542"
    },
    "Poor": {
        "general": "Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects.",
        "sensitive": "People with respiratory or heart disease, children, and older adults should avoid prolonged outdoor exertion. Everyone else should limit prolonged outdoor exertion.",
        "icon": ":material/sentiment_dissatisfied:",
        "color": "#E67E22"
    },
    "Very Poor": {
        "general": "Health alert: The risk of health effects is increased for everyone.",
        "sensitive": "People with respiratory or heart disease, children, and older adults should avoid all outdoor physical activity. Everyone else should limit outdoor exertion.",
        "icon": ":material/warning:",
        "color": "#E5484D"
    },
    "Severe": {
        "general": "Health warning of emergency conditions: everyone is more likely to be affected.",
        "sensitive": "Everyone should avoid all outdoor physical activity. People with respiratory or heart disease should remain indoors and keep activity levels low.",
        "icon": ":material/error:",
        "color": "#8B0000"
    }
}


def get_health_guidance(aqi: float) -> Dict:
    """Returns health guidance for a given AQI value."""
    category_name, _ = get_aqi_category_color(aqi)
    return HEALTH_GUIDANCE.get(category_name, HEALTH_GUIDANCE["Moderate"])


def render_citizen_mode(
    station_data: pd.DataFrame,
    predictions: pd.DataFrame,
    station_name: str,
    decision_date: str
):
    """
    Renders a citizen-friendly simplified view.
    
    Parameters
    ----------
    station_data : pd.DataFrame
        Historical daily data for the station
    predictions : pd.DataFrame
        Forecast data for the station
    station_name : str
        Name of the station
    decision_date : str
        Current date in the data
    """
    st.markdown("### 🏘️ Air Quality in Your Area")
    st.caption(f"**Location:** {station_name} • **Data as of:** {decision_date}")
    
    # Get latest and forecast
    latest_row = station_data.iloc[-1]
    forecast_row = predictions.iloc[-1] if not predictions.empty else None
    
    current_aqi = latest_row["aqi_mean"]
    category_name, category_color = get_aqi_category_color(current_aqi)
    guidance = get_health_guidance(current_aqi)
    
    # Current Status Card
    st.markdown("---")
    st.markdown("#### Current Air Quality Status")
    
    col_status1, col_status2 = st.columns([1, 2])
    
    with col_status1:
        # Big AQI display
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {category_color}22, {category_color}44);
                border: 3px solid {category_color};
                border-radius: 16px;
                padding: 30px;
                text-align: center;
            ">
                <div style="font-size: 3.5rem; font-weight: 800; color: {category_color}; line-height: 1;">
                    {current_aqi:.0f}
                </div>
                <div style="font-size: 1.2rem; font-weight: 600; color: {category_color}; margin-top: 8px;">
                    {category_name}
                </div>
                <div style="font-size: 0.9rem; color: {COLORS['text_muted']}; margin-top: 8px;">
                    Air Quality Index
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col_status2:
        st.markdown(f"**What does this mean?**")
        st.info(guidance["general"], icon=guidance["icon"])
        
        st.markdown("**For sensitive groups (children, elderly, respiratory conditions):**")
        st.warning(guidance["sensitive"], icon=":material/health_and_safety:")
    
    # 7-Day Outlook
    if forecast_row is not None:
        st.markdown("---")
        st.markdown("#### 7-Day Outlook")
        
        forecast_aqi = forecast_row["pred_gb"]
        forecast_cat, forecast_col = get_aqi_category_color(forecast_aqi)
        forecast_low = forecast_row.get("pred_p10", forecast_aqi * 0.8)
        forecast_high = forecast_row.get("pred_p90", forecast_aqi * 1.2)
        
        col_forecast1, col_forecast2, col_forecast3 = st.columns(3)
        
        with col_forecast1:
            st.metric(
                label="Forecast (Tomorrow)",
                value=f"{forecast_aqi:.0f} AQI",
                delta=f"{forecast_aqi - current_aqi:+.0f} from today",
                delta_color="inverse"
            )
        
        with col_forecast2:
            st.metric(
                label="Expected Category",
                value=forecast_cat,
                delta=None
            )
        
        with col_forecast3:
            st.metric(
                label="Uncertainty Range",
                value=f"{forecast_low:.0f} - {forecast_high:.0f}",
                delta=None,
                help="Range represents forecast uncertainty"
            )
        
        st.caption(
            "⚠️ **Note:** Forecasts include uncertainty. Actual air quality may vary. "
            "Check official CPCB sources for current conditions."
        )
    
    # Health Tips
    st.markdown("---")
    st.markdown("#### 💚 Health Protection Tips")
    
    if current_aqi <= 100:
        st.success(
            "Air quality is good today! Perfect for outdoor activities, exercise, and spending time outside.",
            icon=":material/wb_sunny:"
        )
    elif current_aqi <= 200:
        st.warning(
            """
            **Recommended Actions:**
            - Limit strenuous outdoor activity if you have respiratory conditions
            - Close windows during peak traffic hours
            - Consider wearing a mask if you're sensitive to air pollution
            - Monitor air quality before planning outdoor events
            """,
            icon=":material/masks:"
        )
    else:
        st.error(
            """
            **Important Precautions:**
            - ❌ Avoid all outdoor exercise and strenuous activity
            - 🏠 Stay indoors with windows closed
            - 😷 Wear an N95/N99 mask if you must go outside
            - 💨 Use air purifiers indoors if available
            - 🏥 Seek medical attention if you experience breathing difficulties
            """,
            icon=":material/warning:"
        )
    
    # Disclaimer
    st.markdown("---")
    st.caption(
        "**Disclaimer:** This is an educational decision-support tool, not a medical device or official health advisory. "
        "For authoritative air quality data, visit [CPCB's official portal](https://cpcb.nic.in/). "
        "If you experience health symptoms, consult a qualified healthcare provider."
    )


def generate_aqi_card_html(
    station_name: str,
    aqi_value: float,
    category_name: str,
    category_color: str,
    date_str: str,
    trend: str = "→"
) -> str:
    """
    Generates a shareable HTML card for social media / WhatsApp.
    
    Returns HTML string that can be downloaded.
    """
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Air Quality: {station_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .card {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
        }}
        .logo {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        .title {{
            font-size: 1.1rem;
            color: #666;
            margin-bottom: 30px;
        }}
        .aqi-value {{
            font-size: 5rem;
            font-weight: 800;
            color: {category_color};
            line-height: 1;
            margin: 20px 0;
        }}
        .category {{
            font-size: 1.8rem;
            font-weight: 600;
            color: {category_color};
            margin-bottom: 10px;
        }}
        .trend {{
            font-size: 2rem;
            margin: 15px 0;
        }}
        .location {{
            font-size: 1.2rem;
            color: #333;
            margin: 20px 0;
            font-weight: 600;
        }}
        .date {{
            font-size: 0.9rem;
            color: #999;
            margin-top: 20px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #eee;
            font-size: 0.85rem;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">🏙️</div>
        <div class="title">CityPulse: Mumbai</div>
        
        <div class="aqi-value">{aqi_value:.0f}</div>
        <div class="category">{category_name}</div>
        <div class="trend">{trend}</div>
        
        <div class="location">📍 {station_name}</div>
        <div class="date">Data as of: {date_str}</div>
        
        <div class="footer">
            Air Quality Index (AQI)<br>
            Source: CPCB & Open-Meteo
        </div>
    </div>
</body>
</html>
"""
    return html


def render_aqi_card_export(
    station_name: str,
    station_data: pd.DataFrame,
    decision_date: str
):
    """Renders the shareable AQI card export UI."""
    st.markdown("---")
    st.markdown("### 📤 Share Air Quality Status")
    
    latest_row = station_data.iloc[-1]
    current_aqi = latest_row["aqi_mean"]
    category_name, category_color = get_aqi_category_color(current_aqi)
    
    # Determine trend
    if len(station_data) >= 2:
        prev_aqi = station_data.iloc[-2]["aqi_mean"]
        if current_aqi > prev_aqi + 10:
            trend = "📈"
            trend_text = "Worsening"
        elif current_aqi < prev_aqi - 10:
            trend = "📉"
            trend_text = "Improving"
        else:
            trend = "➡️"
            trend_text = "Stable"
    else:
        trend = "➡️"
        trend_text = "Stable"
    
    col_card1, col_card2 = st.columns([2, 1])
    
    with col_card1:
        st.info(
            f"**Current Status:** {current_aqi:.0f} AQI ({category_name}) • Trend: {trend_text} {trend}",
            icon=":material/share:"
        )
        st.caption("Download a shareable card to post on social media or send via WhatsApp.")
    
    with col_card2:
        # Generate card HTML
        card_html = generate_aqi_card_html(
            station_name=station_name,
            aqi_value=current_aqi,
            category_name=category_name,
            category_color=category_color,
            date_str=decision_date,
            trend=trend
        )
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        st.download_button(
            label="📥 Download Card (HTML)",
            data=card_html,
            file_name=f"aqi_card_{station_name.replace(' ', '_')}_{timestamp}.html",
            mime="text/html",
            use_container_width=True,
            help="Save and open in browser to screenshot for sharing"
        )
