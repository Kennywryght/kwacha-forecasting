import os, sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np

# Find CSV
csv_paths = ['data/raw/mwk_usd_final_dataset.csv', '../data/raw/mwk_usd_final_dataset.csv']
df = None
for p in csv_paths:
    if os.path.exists(p):
        df = pd.read_csv(p)
        dc = [c for c in df.columns if c.lower()=='date'][0]
        rc = [c for c in df.columns if c.lower() in ['rate','mwk_usd']][0]
        df = df.rename(columns={dc: 'date', rc: 'rate'})
        df['date'] = pd.to_datetime(df['date'])
        break

if df is not None and len(df) > 30:
    print(f'Training ARIMA on {len(df)} rows...')
    from ml.models.arima_model import ARIMAForecaster
    arima = ARIMAForecaster(use_auto_order=True, max_p=2, max_q=2)  # Faster with lower max
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
