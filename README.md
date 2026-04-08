# GetAround — Delay Analysis & Pricing API

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
└── 04_deployments/
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

This will run 2 MLflow experiments (RandomForest and GradientBoosting), save the best model as `model.pkl in 04_Deployemnet/API`.

To visualize runs:

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

> Update `API_URL` in `streamlit_app.py` to point to the running API before launching the dashboard.

---

## Online

| Service | URL |
|---------|-----|
| API (Hugging Face) | https://Pybnet/getarounda_api.hf.space |
| API docs | https://Pybnet/getarounda_api.hf.space/docs |

### Example API call

```bash
curl -X POST "https://your-space.hf.space/predict" \
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
