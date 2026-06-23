import os, sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np

# Load from database (has projected data to today)
from db.database import SessionLocal
from db.models import ExchangeRate
db = SessionLocal()
rates = db.query(ExchangeRate).order_by(ExchangeRate.date.asc()).all()
db.close()

if len(rates) > 30:
    df = pd.DataFrame([{'date': r.date, 'rate': r.rate} for r in rates])
    df['date'] = pd.to_datetime(df['date'])
    print(f'Loaded {len(df)} rows from database ({df["date"].min().date()} to {df["date"].max().date()})')
    
    # Use feature engineer to create all features for ARIMAX
    print('Engineering features...')
    from ml.pipeline.feature_engineer import engineer_features
    df = engineer_features(df, verbose=False)
    print(f'Features created: {df.shape[1]} columns')
    
    print(f'Training ARIMA on {len(df)} rows...')
    from ml.models.arima_model import ARIMAForecaster
    arima = ARIMAForecaster(use_auto_order=True, max_p=2, max_q=2)
    arima.fit(df)
    arima.save('ml/artifacts/arima.pkl')
    print('ARIMA saved')
    
    print('Training Prophet...')
    from ml.models.prophet_model import ProphetForecaster
    prophet = ProphetForecaster()
    prophet.fit(df)
    prophet.save('ml/artifacts/prophet.pkl')
    print('Prophet saved')
    
    print('Training ARIMAX...')
    from ml.models.arimax_model import ARIMAXForecaster
    arimax = ARIMAXForecaster()
    arimax.fit(df)
    arimax.save('ml/artifacts/arimax.pkl')
    print('ARIMAX saved')
else:
    print('Not enough data for training')