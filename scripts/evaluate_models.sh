#!/bin/bash
# ==========================================
#  KwachaCast - Model Evaluation
#  Usage: bash scripts/evaluate_models.sh
# ==========================================

echo "=========================================="
echo "  KwachaCast - Model Evaluation"
echo "=========================================="
echo ""

cd backend

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "📊 Evaluating all trained models..."
echo ""

python -c "
from ml.models.arima_model import ARIMAForecaster
from ml.models.arimax_model import ARIMAXForecaster
from ml.models.prophet_model import ProphetForecaster
from ml.pipeline.feature_engineer import engineer_features
from ml.utils.metrics import compute_all_metrics, compute_directional_accuracy
from db.database import SessionLocal
from db.models import ExchangeRate
import pandas as pd
import numpy as np
import joblib
import json
import os

# Load data
db = SessionLocal()
rates = db.query(ExchangeRate).order_by(ExchangeRate.date.asc()).all()
df = pd.DataFrame([{'date': r.date, 'rate': float(r.rate)} for r in rates])
df['date'] = pd.to_datetime(df['date'])
db.close()

# Time-based split
train_size = int(len(df) * 0.85)
train_df = df.iloc[:train_size]
test_df = df.iloc[train_size:]

print(f'Training period: {train_df.date.min().date()} to {train_df.date.max().date()}')
print(f'Testing period:  {test_df.date.min().date()} to {test_df.date.max().date()}')
print(f'Test records: {len(test_df)}')
print()

results = {}

# Evaluate ARIMA
print('Evaluating ARIMA...')
try:
    arima = ARIMAForecaster()
    arima.load('ml/artifacts/arima.pkl')
    pred = arima.predict(len(test_df))
    metrics = compute_all_metrics(test_df['rate'].values[:len(pred['predicted'])], pred['predicted'])
    dir_acc = compute_directional_accuracy(test_df['rate'].values[:len(pred['predicted'])], pred['predicted'])
    metrics['directional_accuracy'] = round(dir_acc, 4)
    results['arima'] = {k: round(v, 4) if not np.isnan(v) else 0 for k, v in metrics.items()}
    print(f'  MAPE: {metrics[\"mape\"]:.4f}% | RMSE: {metrics[\"rmse\"]:.4f} | Dir Acc: {dir_acc:.2%}')
except Exception as e:
    print(f'  Failed: {e}')

# Evaluate ARIMAX
print('Evaluating ARIMAX...')
try:
    arimax = ARIMAXForecaster()
    arimax.load('ml/artifacts/arimax.pkl')
    test_eng = engineer_features(test_df.copy(), verbose=False)
    pred = arimax.predict(len(test_df))
    metrics = compute_all_metrics(test_df['rate'].values[:len(pred['predicted'])], pred['predicted'])
    dir_acc = compute_directional_accuracy(test_df['rate'].values[:len(pred['predicted'])], pred['predicted'])
    metrics['directional_accuracy'] = round(dir_acc, 4)
    results['arimax'] = {k: round(v, 4) if not np.isnan(v) else 0 for k, v in metrics.items()}
    print(f'  MAPE: {metrics[\"mape\"]:.4f}% | RMSE: {metrics[\"rmse\"]:.4f} | Dir Acc: {dir_acc:.2%}')
except Exception as e:
    print(f'  Failed: {e}')

# Evaluate XGBoost
print('Evaluating XGBoost...')
try:
    if os.path.exists('ml/artifacts/xgboost_model.joblib'):
        xgb_model = joblib.load('ml/artifacts/xgboost_model.joblib')
        features = joblib.load('ml/artifacts/xgboost_features.joblib')
        test_eng = engineer_features(test_df.copy(), verbose=False)
        X_test = test_eng[features].fillna(0)
        y_pred = xgb_model.predict(X_test)
        metrics = compute_all_metrics(test_df['rate'].values, y_pred)
        dir_acc = compute_directional_accuracy(test_df['rate'].values, y_pred)
        metrics['directional_accuracy'] = round(dir_acc, 4)
        results['xgboost'] = {k: round(v, 4) if not np.isnan(v) else 0 for k, v in metrics.items()}
        print(f'  MAPE: {metrics[\"mape\"]:.4f}% | RMSE: {metrics[\"rmse\"]:.4f} | Dir Acc: {dir_acc:.2%}')
    else:
        print('  Model file not found - train XGBoost first')
except Exception as e:
    print(f'  Failed: {e}')

# Evaluate LightGBM
print('Evaluating LightGBM...')
try:
    if os.path.exists('ml/artifacts/lightgbm_model.joblib'):
        lgb_model = joblib.load('ml/artifacts/lightgbm_model.joblib')
        features = joblib.load('ml/artifacts/lightgbm_features.joblib')
        test_eng = engineer_features(test_df.copy(), verbose=False)
        X_test = test_eng[features].fillna(0)
        y_pred = lgb_model.predict(X_test)
        metrics = compute_all_metrics(test_df['rate'].values, y_pred)
        dir_acc = compute_directional_accuracy(test_df['rate'].values, y_pred)
        metrics['directional_accuracy'] = round(dir_acc, 4)
        results['lightgbm'] = {k: round(v, 4) if not np.isnan(v) else 0 for k, v in metrics.items()}
        print(f'  MAPE: {metrics[\"mape\"]:.4f}% | RMSE: {metrics[\"rmse\"]:.4f} | Dir Acc: {dir_acc:.2%}')
    else:
        print('  Model file not found - train LightGBM first')
except Exception as e:
    print(f'  Failed: {e}')

# Print summary
print()
print('=' * 60)
print('  EVALUATION SUMMARY')
print('=' * 60)
print(f'  {\"Model\":<12} {\"MAPE\":<10} {\"RMSE\":<10} {\"Dir Acc\":<10}')
print(f'  {\"-\"*12} {\"-\"*10} {\"-\"*10} {\"-\"*10}')
for name, metrics in results.items():
    mape = metrics.get('mape', 0)
    rmse = metrics.get('rmse', 0)
    dir_acc = metrics.get('directional_accuracy', 0)
    print(f'  {name:<12} {mape:<10.4f}% {rmse:<10.4f} {dir_acc:<10.2%}')

# Save results
os.makedirs('ml/artifacts', exist_ok=True)
with open('ml/artifacts/evaluation_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print()
print(f'✅ Results saved to ml/artifacts/evaluation_results.json')
"