
.PHONY: help install data refresh eda features model app all test clean-cache

help:
	@echo "CityPulse: Mumbai — Build System"
	@echo ""
	@echo "  make install   - Install dependencies from requirements.txt"
	@echo "  make data      - Run raw ingestion and cleaning pipeline"
	@echo "  make refresh   - Pull latest available data from free sources and rebuild"
	@echo "  make eda       - Generate exploratory data analysis and figures"
	@echo "  make features  - Build leak-free feature set"
	@echo "  make model     - Train models, run holdout evaluation"
	@echo "  make app       - Launch the Streamlit decision dashboard"
	@echo "  make test      - Run all tests"
	@echo "  make all       - Run full end-to-end pipeline (data -> eda -> model)"

install:
	pip install -r requirements.txt

data:
	python -m src.clean.clean_pipeline

refresh:
	@echo "=== Refreshing weather data from Open-Meteo (free, no key) ==="
	python -m src.ingest.weather_download
	@echo "=== Rebuilding cleaned dataset ==="
	python -m src.clean.clean_pipeline
	@echo "=== Rebuilding features ==="
	python -m src.features.build_features
	@echo "=== Retraining models on refreshed data ==="
	python -m src.models.train_evaluate
	python -m src.models.prioritization
	@echo "=== Refresh complete. Run 'make app' to launch. ==="

eda:
	python -m src.features.eda_analysis

features:
	python -m src.features.build_features

model: features
	python -m src.models.train_evaluate
	python -m src.models.prioritization

app:
	streamlit run app.py

test:
	python -m pytest tests/ -v --tb=short

all: data eda model
