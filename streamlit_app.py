"""
CityPulse: Mumbai — Streamlit Community Cloud Default Entry Point Alias
Provides seamless compatibility when deploying with either `streamlit_app.py` or `app.py`.
"""
import runpy

if __name__ == "__main__":
    runpy.run_path("app.py", run_name="__main__")
