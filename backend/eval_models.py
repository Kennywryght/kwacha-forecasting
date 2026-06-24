import os, sys, json
sys.path.insert(0, '.')
import pandas as pd
from db.database import SessionLocal
from db.models import ExchangeRate

db = SessionLocal()
rates = db.query(ExchangeRate).order_by(ExchangeRate.date.asc()).all()
db.close()

df = pd.DataFrame([{'date': r.date, 'rate': float(r.rate)} for r in rates])
df['date'] = pd.to_datetime(df['date'])

from ml.pipeline.feature_engineer import engineer_features
df = engineer_features(df, verbose=False)

train_size = int(len(df) * 0.85)
train_df = df.iloc[:train_size]
test_df = df.iloc[train_size:]

all_metrics = {}

# Evaluate ARIMA
from ml.models.arima_model import ARIMAForecaster
arima = ARIMAForecaster()
arima.load('ml/artifacts/arima.pkl')
m = arima.evaluate(test_df)
all_metrics['arima'] = {
    'mape': float(m.get('mape', 0)),
    'rmse': float(m.get('rmse', 0)),
    'mae': float(m.get('mae', 0))
}
print(f"ARIMA   - MAPE: {all_metrics['arima']['mape']:.2f}%, RMSE: {all_metrics['arima']['rmse']:.2f}, MAE: {all_metrics['arima']['mae']:.2f}")

# Evaluate Prophet
from ml.models.prophet_model import ProphetForecaster
prophet = ProphetForecaster()
prophet.load('ml/artifacts/prophet.pkl')
m = prophet.evaluate(test_df)
all_metrics['prophet'] = {
    'mape': float(m.get('mape', 0)),
    'rmse': float(m.get('rmse', 0)),
    'mae': float(m.get('mae', 0))
}
print(f"Prophet - MAPE: {all_metrics['prophet']['mape']:.2f}%, RMSE: {all_metrics['prophet']['rmse']:.2f}, MAE: {all_metrics['prophet']['mae']:.2f}")

# Evaluate ARIMAX
from ml.models.arimax_model import ARIMAXForecaster
arimax = ARIMAXForecaster()
arimax.load('ml/artifacts/arimax.pkl')
m = arimax.evaluate(test_df)
all_metrics['arimax'] = {
    'mape': float(m.get('mape', 0)),
    'rmse': float(m.get('rmse', 0)),
    'mae': float(m.get('mae', 0))
}
print(f"ARIMAX  - MAPE: {all_metrics['arimax']['mape']:.2f}%, RMSE: {all_metrics['arimax']['rmse']:.2f}, MAE: {all_metrics['arimax']['mae']:.2f}")

os.makedirs('ml/artifacts', exist_ok=True)
with open('ml/artifacts/model_metrics.json', 'w') as f:
    json.dump(all_metrics, f, indent=2)
print('\nMetrics saved: MAPE, RMSE, MAE')
