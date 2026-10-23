"""
CityPulse: Mumbai — Weekly Briefing Export

Generates printable one-page inspection briefings for municipal officers.
Exports as HTML (always) and PDF (if reportlab available).
"""
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from config import DATA_ATTRIBUTION, TEAM_MEMBERS
from theme import get_aqi_category_color

def generate_briefing_html(
    priority_df: pd.DataFrame,
    top_n: int = 5,
    decision_date: str = "",
    target_date: str = "",
    weights: dict = None
) -> str:
    """
    Generates a clean, printable HTML briefing document.
    
    Parameters
    ----------
    priority_df : pd.DataFrame
        Priority rankings table
    top_n : int
        Number of zones to include
    decision_date : str
        Data "as of" date
    target_date : str
        Forecast target date
    weights : dict, optional
        Policy weights used
    
    Returns
    -------
    html : str
        Complete HTML document
    """
    top_zones = priority_df.head(top_n)
    
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CityPulse: Mumbai — Weekly Inspection Briefing</title>
    <style>
        @page {
            size: A4;
            margin: 1.5cm;
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', 'Inter', -apple-system, system-ui, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #1a1a1a;
            background: #ffffff;
            padding: 20px;
        }
        .header {
            border-bottom: 3px solid #0066cc;
            padding-bottom: 12px;
            margin-bottom: 16px;
        }
        .header h1 {
            font-size: 20pt;
            font-weight: 700;
            color: #0066cc;
            margin-bottom: 4px;
        }
        .header .meta {
            font-size: 9pt;
            color: #666666;
        }
        .section {
            margin-bottom: 18px;
        }
        .section h2 {
            font-size: 13pt;
            font-weight: 600;
            color: #0066cc;
            margin-bottom: 8px;
            border-bottom: 1px solid #cccccc;
            padding-bottom: 4px;
        }
        .zone-card {
            background: #f8f9fa;
            border-left: 4px solid #0066cc;
            padding: 10px 12px;
            margin-bottom: 10px;
            page-break-inside: avoid;
        }
        .zone-card .title {
            font-size: 12pt;
            font-weight: 700;
            margin-bottom: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .zone-card .aqi-badge {
            background: #ffffff;
            border: 2px solid #666666;
            border-radius: 4px;
            padding: 2px 8px;
            font-weight: 700;
            font-size: 10pt;
        }
        .zone-card .metrics {
            font-size: 9.5pt;
            color: #444444;
            margin-bottom: 6px;
        }
        .zone-card .action {
            font-size: 10pt;
            color: #1a1a1a;
            background: #ffffff;
            padding: 8px;
            border-radius: 4px;
            margin-top: 6px;
        }
        .zone-card .evidence {
            font-size: 9pt;
            color: #666666;
            margin-top: 4px;
        }
        .footer {
            margin-top: 20px;
            padding-top: 12px;
            border-top: 2px solid #cccccc;
            font-size: 8pt;
            color: #666666;
            line-height: 1.4;
        }
        .weights-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 8px;
            font-size: 9pt;
        }
        .weights-table th, .weights-table td {
            padding: 4px 8px;
            text-align: left;
            border-bottom: 1px solid #dddddd;
        }
        .weights-table th {
            background: #f0f0f0;
            font-weight: 600;
        }
    </style>
</head>
<body>
"""
    
    generation_timestamp = datetime.now().strftime("%d %B %Y at %H:%M IST")
    html += f"""
    <div class="header">
        <h1>🏙️ CityPulse: Mumbai — Weekly Inspection Briefing</h1>
        <div class="meta">
            <strong>BMC / MPCB Environmental Enforcement Division</strong><br>
            Data as of: <strong>{decision_date}</strong> | 
            Target Forecast Date: <strong>{target_date}</strong> | 
            Generated: {generation_timestamp}
        </div>
    </div>
"""
    
    avg_score = top_zones["priority_score"].mean()
    high_risk_count = (top_zones["latest_aqi"] > 150).sum()
    
    html += f"""
    <div class="section">
        <h2>Executive Summary</h2>
        <p>
            This briefing identifies the <strong>Top {top_n}</strong> priority zones for municipal inspection and 
            intervention based on multi-criteria risk scoring. The average priority score is <strong>{avg_score:.1f}/100</strong>, 
            with <strong>{high_risk_count}/{top_n}</strong> zones currently exceeding the Moderate threshold (AQI &gt; 150).
        </p>
    </div>
"""
    
    html += """
    <div class="section">
        <h2>Priority Inspection Zones</h2>
"""
    
    for idx, row in top_zones.iterrows():
        cat_name, cat_color = get_aqi_category_color(row["latest_aqi"])
        
        border_colors = {
            "Good": "#2ECC71",
            "Satisfactory": "#3498DB",
            "Moderate": "#F5C542",
            "Poor": "#E67E22",
            "Very Poor": "#E5484D",
            "Severe": "#8B0000"
        }
        border = border_colors.get(cat_name, "#0066cc")
        
        html += f"""
        <div class="zone-card" style="border-left-color: {border};">
            <div class="title">
                <span>#{row['rank']}. {row['station']}</span>
                <span class="aqi-badge" style="border-color: {border}; color: {border};">{row['latest_aqi']:.0f} AQI</span>
            </div>
            <div class="metrics">
                <strong>Zone:</strong> {row.get('zone', 'MMR')} | 
                <strong>Score:</strong> {row['priority_score']:.1f}/100 | 
                <strong>Category:</strong> {cat_name} | 
                <strong>Risk Forecast:</strong> {row.get('forecast_prob_unhealthy', 0)*100:.0f}% chance AQI &gt; 200
            </div>
            <div class="action">
                <strong>→ Recommended Action:</strong><br>
                {row.get('recommended_action', 'Standard monitoring protocol.')}
            </div>
            <div class="evidence">
                <strong>Evidence:</strong> {row.get('evidence_basis', 'Based on historical observations.')}
            </div>
        </div>
"""
    
    html += """
    </div>
"""
    
    if weights:
        html += """
    <div class="section">
        <h2>Prioritization Policy Weights</h2>
        <table class="weights-table">
            <thead>
                <tr>
                    <th>Criterion</th>
                    <th>Weight</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
"""
        weight_descriptions = {
            "w_exp": ("Recent Exposure", "7-day mean AQI relative to standards"),
            "w_pers": ("Persistence Shock", "Days exceeding Moderate threshold"),
            "w_trend": ("Trend Acceleration", "Rate of worsening"),
            "w_fore": ("Forecast Risk", "Probability of unhealthy conditions"),
            "w_gap": ("Vulnerability", "Environmental context factors"),
        }
        
        for key, (name, desc) in weight_descriptions.items():
            weight_val = weights.get(key, 0.0)
            html += f"""
                <tr>
                    <td>{name}</td>
                    <td>{weight_val:.2f} ({weight_val*100:.0f}%)</td>
                    <td>{desc}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
    </div>
"""
    
    html += f"""
    <div class="footer">
        <p>
            <strong>Data Sources:</strong> {DATA_ATTRIBUTION}<br>
            <strong>Disclaimer:</strong> This briefing is a decision-support tool for municipal environmental planning. 
            It is NOT an official statutory warning system. Physical inspection and verification are required before 
            enforcement actions. All forecasts include uncertainty and should be interpreted with caution.<br>
            <strong>Built by:</strong> {TEAM_MEMBERS} for HackAMatch 1.0<br>
            <strong>License:</strong> MIT License | Open-source project available for public benefit
        </p>
    </div>
</body>
</html>
"""
    
    return html

def try_export_pdf(html_content: str) -> Optional[bytes]:
    """
    Attempts to export HTML to PDF using available libraries.
    Returns None if no PDF library is available.
    """
    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        return pdf_bytes
    except ImportError:
        pass
    
    try:
        from xhtml2pdf import pisa
        output = io.BytesIO()
        pisa.CreatePDF(io.StringIO(html_content), dest=output)
        pdf_bytes = output.getvalue()
        if pdf_bytes:
            return pdf_bytes
    except ImportError:
        pass
    
    return None

def render_briefing_export_ui(
    priority_df: pd.DataFrame,
    decision_date: str,
    target_date: str,
    weights: dict,
    capacity_n: int = 5
):
    """
    Renders the briefing export UI in Streamlit.
    
    Displays download buttons for HTML (always) and PDF (if available).
    """
    st.markdown("---")
    st.markdown(f"### 📄 Weekly Briefing Export")
    st.caption(
        "Generate a printable one-page briefing for field inspectors. "
        "Includes top priority zones, recommended actions, evidence basis, and data attribution."
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info(
            f"**Ready to export:** Top {capacity_n} zones based on current policy weights. "
            f"Data as of {decision_date}, forecasting for {target_date}.",
            icon=":material/info:"
        )
    
    with col2:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        html_content = generate_briefing_html(
            priority_df=priority_df,
            top_n=capacity_n,
            decision_date=decision_date,
            target_date=target_date,
            weights=weights
        )
        
        st.download_button(
            label="📥 Download HTML",
            data=html_content,
            file_name=f"citypulse_briefing_{timestamp}.html",
            mime="text/html",
            width='stretch',
            help="Download as HTML (opens in any browser, printable)"
        )
        
        pdf_bytes = try_export_pdf(html_content)
        if pdf_bytes:
            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=f"citypulse_briefing_{timestamp}.pdf",
                mime="application/pdf",
                width='stretch',
                help="Download as PDF (ready to print)"
            )
        else:
            st.caption("💡 PDF export unavailable (install weasyprint or xhtml2pdf)")
