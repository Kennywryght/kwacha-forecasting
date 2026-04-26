import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

import pytest
from fastapi.testclient import TestClient
from main import app
from api.routes.forecasts import set_models

# ── Pre-load models into the test app ─────────────────────────────────────────
def _load_test_models():
    from ml.models.arima_model    import ARIMAForecaster
    from ml.models.arimax_model   import ARIMAXForecaster
    from ml.models.lstm_model     import LSTMForecaster
    from ml.models.ensemble_model import EnsembleForecaster

    artifacts = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../backend/ml/artifacts")
    )
    arima  = ARIMAForecaster();  arima.load(os.path.join(artifacts, "arima.pkl"))
    arimax = ARIMAXForecaster(); arimax.load(os.path.join(artifacts, "arimax.pkl"))
    lstm   = LSTMForecaster();   lstm.load(os.path.join(artifacts, "lstm.pt"))
    ensemble = EnsembleForecaster(arima, arimax, lstm)
    ensemble.load(os.path.join(artifacts, "ensemble.pkl"))
    set_models({"arima": arima, "arimax": arimax, "lstm": lstm, "ensemble": ensemble})

_load_test_models()
client = TestClient(app)


def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "running"
    assert "version" in data


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_rates_latest():
    res = client.get("/api/v1/rates/latest")
    assert res.status_code == 200
    data = res.json()
    assert "rate" in data
    assert "date" in data
    assert data["rate"] > 0
    print(f"\n  Latest rate: {data['rate']} on {data['date']}")


def test_rates_history_default():
    res = client.get("/api/v1/rates/history")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    assert len(data["data"]) > 0
    assert data["total"] > 0


def test_rates_history_custom_range():
    res = client.get("/api/v1/rates/history?start=2024-01-01&end=2024-12-31")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) > 0


def test_rates_status():
    res = client.get("/api/v1/rates/status")
    assert res.status_code == 200
    data = res.json()
    assert "latest_date"   in data
    assert "total_records" in data
    assert "is_stale"      in data


def test_forecast_generate_7day():
    res = client.post("/api/v1/forecasts/generate?horizon=7")
    assert res.status_code == 200
    data = res.json()
    assert "results"      in data
    assert data["horizon_days"] == 7


def test_forecast_generate_30day():
    res = client.post("/api/v1/forecasts/generate?horizon=30")
    assert res.status_code == 200
    data = res.json()
    assert data["horizon_days"] == 30


def test_forecast_latest_ensemble():
    client.post("/api/v1/forecasts/generate?horizon=7")
    res = client.get("/api/v1/forecasts/latest?horizon=7&model=ensemble")
    assert res.status_code == 200
    data = res.json()
    assert "forecasts" in data
    assert len(data["forecasts"]) == 7
    for point in data["forecasts"]:
        assert point["predicted_rate"] > 0
        assert "target_date" in point


def test_forecast_all_models():
    client.post("/api/v1/forecasts/generate?horizon=7")
    res = client.get("/api/v1/forecasts/all?horizon=7")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0


def test_models_performance():
    res = client.get("/api/v1/models/performance")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data


def test_pipeline_status():
    res = client.get("/api/v1/pipeline/status")
    assert res.status_code == 200
    data = res.json()
    assert "data_latest_date" in data
    assert "total_rates"      in data


def test_invalid_endpoint_returns_404():
    res = client.get("/api/v1/nonexistent")
    assert res.status_code == 404