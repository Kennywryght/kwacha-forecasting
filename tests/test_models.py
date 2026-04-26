import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

import pytest
import pandas as pd

ARTIFACTS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../backend/ml/artifacts")
)


def load_test_data():
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../data/processed/mwk_usd_clean.csv")
    )
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[df["date"] >= "2020-01-01"].copy()
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def test_arima_artifact_exists():
    path = os.path.join(ARTIFACTS, "arima.pkl")
    assert os.path.exists(path), "arima.pkl not found — run retrain_models.py first"


def test_arimax_artifact_exists():
    path = os.path.join(ARTIFACTS, "arimax.pkl")
    assert os.path.exists(path), "arimax.pkl not found — run retrain_models.py first"


def test_lstm_artifact_exists():
    path = os.path.join(ARTIFACTS, "lstm.pt")
    assert os.path.exists(path), "lstm.pt not found — run retrain_models.py first"


def test_ensemble_artifact_exists():
    path = os.path.join(ARTIFACTS, "ensemble.pkl")
    assert os.path.exists(path), "ensemble.pkl not found — run retrain_models.py first"


def test_arima_loads_and_predicts():
    from ml.models.arima_model import ARIMAForecaster
    model = ARIMAForecaster()
    model.load(os.path.join(ARTIFACTS, "arima.pkl"))
    assert model.is_fitted
    result = model.predict(7)
    assert len(result["dates"])       == 7
    assert len(result["predicted"])   == 7
    assert len(result["lower_bound"]) == 7
    assert len(result["upper_bound"]) == 7
    assert all(r > 0 for r in result["predicted"])
    print(f"\n  ARIMA 7-day forecast: {result['predicted']}")


def test_arimax_loads_and_predicts():
    from ml.models.arimax_model import ARIMAXForecaster
    model = ARIMAXForecaster()
    model.load(os.path.join(ARTIFACTS, "arimax.pkl"))
    assert model.is_fitted
    result = model.predict(7)
    assert len(result["dates"])     == 7
    assert all(r > 0 for r in result["predicted"])
    print(f"\n  ARIMAX 7-day forecast: {result['predicted']}")


def test_lstm_loads_and_predicts():
    from ml.models.lstm_model import LSTMForecaster
    model = LSTMForecaster()
    model.load(os.path.join(ARTIFACTS, "lstm.pt"))
    assert model.is_fitted
    result = model.predict(7)
    assert len(result["dates"])     == 7
    assert all(r > 0 for r in result["predicted"])
    print(f"\n  LSTM 7-day forecast: {result['predicted']}")


def test_ensemble_loads_and_predicts():
    from ml.models.arima_model    import ARIMAForecaster
    from ml.models.arimax_model   import ARIMAXForecaster
    from ml.models.lstm_model     import LSTMForecaster
    from ml.models.ensemble_model import EnsembleForecaster

    arima  = ARIMAForecaster();  arima.load(os.path.join(ARTIFACTS, "arima.pkl"))
    arimax = ARIMAXForecaster(); arimax.load(os.path.join(ARTIFACTS, "arimax.pkl"))
    lstm   = LSTMForecaster();   lstm.load(os.path.join(ARTIFACTS, "lstm.pt"))

    ensemble = EnsembleForecaster(arima, arimax, lstm)
    ensemble.load(os.path.join(ARTIFACTS, "ensemble.pkl"))
    assert ensemble.is_fitted

    result = ensemble.predict(7)
    assert len(result["dates"])   == 7
    assert all(r > 0 for r in result["predicted"])
    print(f"\n  Ensemble 7-day forecast: {result['predicted']}")


def test_forecast_horizons_1_7_30():
    from ml.models.arima_model import ARIMAForecaster
    model = ARIMAForecaster()
    model.load(os.path.join(ARTIFACTS, "arima.pkl"))
    for h in [1, 7, 30]:
        result = model.predict(h)
        assert len(result["predicted"]) == h, f"Expected {h} predictions"


def test_confidence_intervals_valid():
    from ml.models.arima_model import ARIMAForecaster
    model = ARIMAForecaster()
    model.load(os.path.join(ARTIFACTS, "arima.pkl"))
    result = model.predict(7)
    for lo, pred, hi in zip(result["lower_bound"], result["predicted"], result["upper_bound"]):
        assert lo <= pred <= hi, f"CI invalid: {lo} <= {pred} <= {hi}"


def test_model_metrics_exist():
    from ml.models.arima_model import ARIMAForecaster
    model = ARIMAForecaster()
    model.load(os.path.join(ARTIFACTS, "arima.pkl"))
    assert "rmse" in model.metrics
    assert "mape" in model.metrics
    assert "mae"  in model.metrics
    assert model.metrics["mape"] < 5.0, "MAPE exceeds 5% threshold"