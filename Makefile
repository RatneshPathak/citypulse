
.PHONY: help install data eda features model app all

help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies from requirements.txt"
	@echo "  make data     - Run raw ingestion and cleaning pipeline"
	@echo "  make eda      - Generate exploratory data analysis and figures"
	@echo "  make model    - Train models, run holdout evaluation, and update EVALUATION.md"
	@echo "  make app      - Launch the Streamlit decision dashboard"
	@echo "  make all      - Run full end-to-end pipeline (clean -> eda -> model)"

install:
	pip install -r requirements.txt

data:
	python -m src.clean.clean_pipeline

eda:
	python -m src.features.eda_analysis

features:
	python -m src.features.build_features

model: features
	python -m src.models.train_evaluate
	python -m src.models.prioritization

app:
	streamlit run app.py

all: data eda model
