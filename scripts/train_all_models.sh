#!/bin/bash
# ==========================================
#  KwachaCast - Model Training Pipeline
#  Usage: bash scripts/train_all_models.sh
# ==========================================

echo "=========================================="
echo "  KwachaCast - Model Training Pipeline"
echo "=========================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "backend/venv" ]; then
    source backend/venv/bin/activate
fi

echo "📊 Step 1: Loading data from database..."
cd backend
python -c "
from db.database import SessionLocal
from db.models import ExchangeRate
import pandas as pd

db = SessionLocal()
rates = db.query(ExchangeRate).order_by(ExchangeRate.date.asc()).all()
df = pd.DataFrame([{'date': r.date, 'rate': float(r.rate)} for r in rates])
df.to_csv('../data/processed/training_data.csv', index=False)
print(f'Loaded {len(df)} rows from {df.date.min().date()} to {df.date.max().date()}')
db.close()
"

echo ""
echo "🔧 Step 2: Engineering features..."
python -c "
from ml.pipeline.feature_engineer import engineer_features
import pandas as pd

df = pd.read_csv('../data/processed/training_data.csv')
df['date'] = pd.to_datetime(df['date'])
df_eng = engineer_features(df, verbose=False)
df_eng.to_csv('../data/processed/features_engineered.csv', index=False)
print(f'Created {df_eng.shape[1]} features from {df_eng.shape[0]} rows')
"

echo ""
echo "🤖 Step 3: Training ARIMA, Prophet, and ARIMAX..."
python train_models.py

echo ""
echo "✅ Training complete!"
echo "Models saved to backend/ml/artifacts/"
echo ""
echo "📝 Note: XGBoost and LightGBM require the Colab notebook"
echo "   Run the notebook at: backend/ml/notebooks/train_ml_models.ipynb"