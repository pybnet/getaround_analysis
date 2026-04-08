import os
import io
import boto3
import joblib
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List

# Chargement modèle

def load_model():
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "eu-central-1"),
    )
    buffer = io.BytesIO()
    s3.download_fileobj(
    os.getenv("AWS_BUCKET_NAME", "pybnet-s3"),
    os.getenv("AWS_MODEL_PATH", "getaround/models/model.pkl"),
    buffer,
  )
    buffer.seek(0)
    return joblib.load(buffer)

model = load_model()

app = FastAPI(
    title="GetAround Pricing API",
    description="Predicts the optimal daily rental price for a car listed on GetAround.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

class CarFeatures(BaseModel):
    model_key: str
    mileage: int
    engine_power: int
    fuel: str
    paint_color: str
    car_type: str
    private_parking_available: bool
    has_gps: bool
    has_air_conditioning: bool
    automatic_car: bool
    has_getaround_connect: bool
    has_speed_regulator: bool
    winter_tires: bool


class PredictRequest(BaseModel):
    input: List[CarFeatures]


class PredictResponse(BaseModel):
    prediction: List[float]

# Endpoints

@app.post("/predict", response_model=PredictResponse, tags=["Prediction"])
def predict(request: PredictRequest):
    """
    Predict the optimal daily rental price (€/day) for one or several cars.
    Accepts a JSON body with an `input` key containing a list of car objects.
    Returns a `prediction` list of floats in the same order.
    """
    df = pd.DataFrame([car.model_dump() for car in request.input])
    predictions = model.predict(df).tolist()
    predictions = [round(p, 2) for p in predictions]
    return PredictResponse(prediction=predictions)


@app.get("/health", tags=["Monitoring"])
def health():
    """Simple health check."""
    return {"status": "ok"}


# Docs

DOCS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>GetAround Pricing API – Documentation</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #f5f7fa;
      color: #1a1a2e;
      line-height: 1.6;
    }
    header {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
      color: #fff;
      padding: 48px 40px 36px;
    }
    header h1 { font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; }
    header p  { margin-top: 8px; opacity: 0.75; font-size: 1rem; }
    .badge {
      display: inline-block; margin-top: 14px;
      background: #e94560; color: #fff;
      padding: 3px 12px; border-radius: 999px; font-size: 0.75rem; font-weight: 600;
    }
    main { max-width: 860px; margin: 48px auto; padding: 0 24px 80px; }
    section { margin-bottom: 48px; }
    h2 { font-size: 1.25rem; font-weight: 700; margin-bottom: 16px; color: #0f3460;
         border-left: 4px solid #e94560; padding-left: 12px; }
    h3 { font-size: 1rem; font-weight: 600; margin: 20px 0 8px; }
    .endpoint-card {
      background: #fff; border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,.07);
      overflow: hidden; margin-bottom: 28px;
    }
    .endpoint-header {
      display: flex; align-items: center; gap: 14px;
      padding: 18px 24px; border-bottom: 1px solid #eef0f4;
    }
    .method {
      font-size: 0.7rem; font-weight: 800; letter-spacing: 1px;
      padding: 4px 10px; border-radius: 6px; flex-shrink: 0;
    }
    .method.post { background: #e0f0e9; color: #1a7a4a; }
    .method.get  { background: #e0eaf9; color: #1a4a9a; }
    .path { font-family: 'Courier New', monospace; font-size: 1rem; font-weight: 600; }
    .description { color: #555; font-size: 0.9rem; margin-top: 4px; }
    .endpoint-body { padding: 20px 24px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-top: 8px; }
    th { text-align: left; padding: 8px 12px; background: #f0f4ff;
         font-weight: 600; color: #0f3460; border-bottom: 2px solid #e0e8ff; }
    td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }
    tr:last-child td { border-bottom: none; }
    code {
      background: #f0f4ff; border-radius: 4px;
      padding: 1px 6px; font-family: 'Courier New', monospace; font-size: 0.82rem;
      color: #0f3460;
    }
    pre {
      background: #1a1a2e; color: #e2e8f0;
      border-radius: 10px; padding: 20px; overflow-x: auto;
      font-size: 0.82rem; line-height: 1.7; margin-top: 12px;
    }
    .model-section { background: #fff; border-radius: 12px;
                     box-shadow: 0 2px 12px rgba(0,0,0,.07); padding: 24px; }
    .metric { display: inline-block; background: #e0f0e9; color: #1a7a4a;
              border-radius: 8px; padding: 6px 16px; font-weight: 700;
              font-size: 0.9rem; margin: 4px 4px 0 0; }
  </style>
</head>
<body>
<header>
  <h1>🚗 GetAround Pricing API</h1>
  <p>Predicts the optimal daily rental price for cars listed on GetAround using Machine Learning.</p>
  <span class="badge">v1.0.0</span>
</header>
<main>

  <section>
    <h2>Overview</h2>
    <p>This API exposes a machine learning model trained on GetAround rental data to suggest
    competitive daily prices for car owners. It accepts structured car features and returns
    a predicted price in <strong>€/day</strong>.</p>
    <br>
    <p><strong>Base URL:</strong> <code>https://pybnet-getarounda-api.hf.space</code></p>
  </section>

  <section>
    <h2>Endpoints</h2>

    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method post">POST</span>
        <div>
          <div class="path">/predict</div>
          <div class="description">Predict daily rental price for one or several cars.</div>
        </div>
      </div>
      <div class="endpoint-body">
        <h3>Request Body</h3>
        <table>
          <tr><th>Field</th><th>Type</th><th>Description</th></tr>
          <tr><td><code>input</code></td><td>array of <em>CarFeatures</em></td><td>List of cars to price</td></tr>
        </table>

        <h3>CarFeatures object</h3>
        <table>
          <tr><th>Field</th><th>Type</th><th>Example values</th></tr>
          <tr><td><code>model_key</code></td><td>string</td><td><code>"Renault"</code>, <code>"BMW"</code>, <code>"Citroën"</code>…</td></tr>
          <tr><td><code>mileage</code></td><td>integer</td><td><code>85000</code></td></tr>
          <tr><td><code>engine_power</code></td><td>integer</td><td><code>120</code></td></tr>
          <tr><td><code>fuel</code></td><td>string</td><td><code>"diesel"</code>, <code>"petrol"</code>, <code>"hybrid_petrol"</code>, <code>"electro"</code></td></tr>
          <tr><td><code>paint_color</code></td><td>string</td><td><code>"black"</code>, <code>"white"</code>, <code>"grey"</code>, <code>"blue"</code>…</td></tr>
          <tr><td><code>car_type</code></td><td>string</td><td><code>"sedan"</code>, <code>"suv"</code>, <code>"estate"</code>, <code>"hatchback"</code>…</td></tr>
          <tr><td><code>private_parking_available</code></td><td>boolean</td><td><code>true</code> / <code>false</code></td></tr>
          <tr><td><code>has_gps</code></td><td>boolean</td><td><code>true</code> / <code>false</code></td></tr>
          <tr><td><code>has_air_conditioning</code></td><td>boolean</td><td><code>true</code> / <code>false</code></td></tr>
          <tr><td><code>automatic_car</code></td><td>boolean</td><td><code>true</code> / <code>false</code></td></tr>
          <tr><td><code>has_getaround_connect</code></td><td>boolean</td><td><code>true</code> / <code>false</code></td></tr>
          <tr><td><code>has_speed_regulator</code></td><td>boolean</td><td><code>true</code> / <code>false</code></td></tr>
          <tr><td><code>winter_tires</code></td><td>boolean</td><td><code>true</code> / <code>false</code></td></tr>
        </table>

        <h3>Response</h3>
        <table>
          <tr><th>Field</th><th>Type</th><th>Description</th></tr>
          <tr><td><code>prediction</code></td><td>array of float</td><td>Predicted price (€/day) for each input car, in the same order</td></tr>
        </table>

        <h3>Example – curl</h3>
        <pre>curl -X POST "https://pybnet-getarounda-api.hf.space/predict" \\
     -H "Content-Type: application/json" \\
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
}'</pre>

        <h3>Example – Python</h3>
        <pre>import requests

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
# {"prediction": [118.45]}</pre>
      </div>
    </div>

    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method get">GET</span>
        <div>
          <div class="path">/health</div>
          <div class="description">Check that the API is running.</div>
        </div>
      </div>
      <div class="endpoint-body">
        <h3>Response</h3>
        <pre>{"status": "ok"}</pre>
      </div>
    </div>
  </section>

  <section>
    <h2>Machine Learning Model</h2>
    <div class="model-section">
      <p><strong>Algorithm:</strong> Gradient Boosting Regressor (scikit-learn)</p>
      <p style="margin-top:8px"><strong>Training data:</strong> 4 843 GetAround listings</p>
      <p style="margin-top:8px"><strong>Features:</strong> car brand, mileage, engine power, fuel type,
      paint colour, car body type, and 7 boolean equipment flags.</p>
      <p style="margin-top:8px"><strong>Performance on test set (20%):</strong></p>
      <div style="margin-top:10px">
        <span class="metric">MAE ≈ 11 €/day</span>
        <span class="metric">R² ≈ 0.74</span>
      </div>
    </div>
  </section>

</main>
</body>
</html>"""


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
def custom_docs():
    return DOCS_HTML