# 🚗 GetAround — Delay Analysis & Pricing Optimization

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![MLflow](https://img.shields.io/badge/MLflow-2.21-orange)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Spaces-yellow)

GetAround is a car-sharing platform (the Airbnb for cars).
Goals:

1. Delay analysis — Help the Product Manager decide on a minimum delay between two rentals (threshold & scope) to reduce friction caused by late checkouts.
2. Pricing optimization — Provide car owners with ML-based daily price suggestions.

---

## Project structure

```
getaround_analysis/
├── 01_data/
│   ├── get_around_delay_analysis.xlsx
│   └── get_around_pricing_project.csv
├── 02_eda/
│   └── eda.ipynb                  # Exploratory Data Analysis
├── 03_models/
│   ├── train.py                   # Model training with MLflow tracking
│   ├── model.pkl                  # Serialized best model (gitignored)
│   └── mlruns/                    # MLflow runs (gitignored)
└── 04_deployement/
    ├── API/
    │   ├── api_app.py             # FastAPI — /predict & /docs endpoints
    │   ├── model.pkl              # Serialized best model (gitignored)
    │   ├── Dockerfile             # For deployment on Hugging Face
    │   └── requirements.txt       # API dependencies
    └── Dashboard/
        └── streamlit_app.py       # Streamlit dashboard (local only)
```

---

## Local setup

### Prerequisites

Create and activate the conda environment:

```bash
conda env create -f environment.yml
conda activate ml
```

### 1. Train the model

```bash
cd 03_models
python train.py
```

Runs **4 MLflow experiments** (RandomForest, GradientBoosting, GradientBoosting + GridSearch) and selects the best model based on a **R²_test / (1 + ΔR²)** score that penalizes overfitting. The best model is saved as `model.pkl` and uploaded to S3.

To visualize MLflow runs:

```bash
cd 03_models
mlflow ui --port 5000
# → http://localhost:5000
```

### 2. Run the API locally

```bash
cd 04_deployments/API
cp ../../03_models/model.pkl .
uvicorn api_app:app --reload --port 8000
# → http://localhost:8000/docs
# → http://localhost:8000/predict
```

### 3. Run the dashboard locally

```bash
cd 04_deployments/Dashboard
streamlit run streamlit_app.py
# → http://localhost:8501
```

The dashboard connects to the deployed API on Hugging Face to serve price predictions. Make sure `API_URL` in `streamlit_app.py` points to the correct endpoint.

---

## 📊 Dashboard

The Streamlit dashboard is structured in 5 sections:

| Section | Content |
|---------|---------|
| **Vue globale** | KPIs, breakdown by checkin type and status |
| **Retards au checkout** | Delay distribution, boxplot mobile vs connect |
| **Impact sur la location suivante** | How late returns affect the next driver |
| **Simulation de seuils** | Interactive slider to test threshold & scope trade-offs |
| **Estimation du prix** | Form to get a price prediction from the ML model |

---


## 🤗 API — Hugging Face

| Service | URL |
|---------|-----|
| API (Hugging Face) | https://pybnet-getarounda-api.hf.space |
| API docs | https://pybnet-getarounda-api.hf.space/docs |

The API is deployed on Hugging Face Spaces using Docker.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Check the API is running |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Full HTML documentation |
| `POST` | `/predict` | Predict daily rental price |

### Example API call

```bash
curl -X POST "https://pybnet/getarounda_api.hf.space/predict" \
     -H "Content-Type: application/json" \
     -d '{
  "input": [{
    "model_key": "Renault",
    "mileage": 85000,
    "engine_power": 120,
    "fuel": "diesel",
    "paint_color": "black",
    "car_type": "sedan",
    "private_parking_available": true,
    "has_gps": true,
    "has_air_conditioning": true,
    "automatic_car": false,
    "has_getaround_connect": true,
    "has_speed_regulator": true,
    "winter_tires": false
  }]
}'
```

```json
{"prediction": [118.45]}
```

### Python

```python
import requests

response = requests.post("https://pybnet-getarounda-api.hf.space/predict", json={
    "input": [{
        "model_key": "Renault",
        "mileage": 85000,
        "engine_power": 120,
        "fuel": "diesel",
        "paint_color": "black",
        "car_type": "sedan",
        "private_parking_available": True,
        "has_gps": True,
        "has_air_conditioning": True,
        "automatic_car": False,
        "has_getaround_connect": True,
        "has_speed_regulator": True,
        "winter_tires": False
    }]
})
print(response.json())
# {"prediction": [118.45]}
```

### Deploy to Hugging Face

```bash
# From the project root, push only the API folder to HF Space
git push https://huggingface.co/spaces/Pybnet/getarounda_api \
  `git subtree split --prefix=04_Deployements/API main`:main --force
```

---

## 🤖 Machine Learning

### Models tested

| Model | Description |
|-------|-------------|
| **Random Forest** | Ensemble of trees trained in parallel via bagging — predictions are averaged to reduce variance |
| **Gradient Boosting** | Sequential trees where each corrects the errors of the previous one via boosting |
| **Gradient Boosting + GridSearch** | Same algorithm with hyperparameters (`n_estimators`, `learning_rate`, `max_depth`) optimized automatically via cross-validation |

### Model selection

The best model is selected based on a custom score that penalizes overfitting:

```
score = R²_test / (1 + ΔR²)    where ΔR² = R²_train - R²_test
```

### Results

| Model | R²_train | R²_test | ΔR² | Score |
|-------|----------|---------|-----|-------|
| RandomForest | 0.9657 | 0.7341 | 0.2316 | 0.5937 |
| **GradientBoosting** ✅ | **0.8158** | **0.7443** | **0.0715** | **0.6937** |
| GradientBoosting + GridSearch | 0.9063 | 0.7473 | 0.1590 | 0.6449 |

**Gradient Boosting** selected — best balance between performance and generalization.

### Metrics

| Metric | Meaning in this context |
|--------|------------------------|
| **MAE** | Average error in €/day — the model is off by ~11 €/day on average |
| **RMSE** | Same as MAE but penalizes large errors more — useful to detect outlier predictions |
| **R²** | Share of price variance explained by the model — 0.74 means 74% of price differences between cars are captured |