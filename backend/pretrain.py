import os, sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import json

# Models directory - persists because it's in the repo
ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml', 'artifacts')
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

arima_path = os.path.join(ARTIFACTS_DIR, 'arima.pkl')
prophet_path = os.path.join(ARTIFACTS_DIR, 'prophet.pkl')
arimax_path = os.path.join(ARTIFACTS_DIR, 'arimax.pkl')
metrics_path = os.path.join(ARTIFACTS_DIR, 'model_metrics.json')

# Check if models AND metrics exist
models_exist = all(os.path.exists(p) for p in [arima_path, prophet_path, arimax_path])
metrics_exist = os.path.exists(metrics_path)

if models_exist and metrics_exist:
    with open(metrics_path) as f:
        saved_metrics = json.load(f)
    print(f'✅ All {len(saved_metrics)} models and metrics exist - skipping training')
else:
    print('⚠️ Training required...')
    
    from db.database import SessionLocal
    from db.models import ExchangeRate
    db = SessionLocal()
    rates = db.query(ExchangeRate).order_by(ExchangeRate.date.asc()).all()
    db.close()

    if len(rates) > 30:
        df = pd.DataFrame([{'date': r.date, 'rate': r.rate} for r in rates])
        df['date'] = pd.to_datetime(df['date'])
        print(f'Loaded {len(df)} rows ({df["date"].min().date()} to {df["date"].max().date()})')
        
        from ml.pipeline.feature_engineer import engineer_features
        df = engineer_features(df, verbose=False)
        print(f'{df.shape[1]} features created')
        
        # Split for evaluation
        train_size = int(len(df) * 0.85)
        train_df = df.iloc[:train_size]
        test_df = df.iloc[train_size:]
        
        all_metrics = {}
        
        # Train & Evaluate ARIMA
        if not os.path.exists(arima_path):
            print(f'Training ARIMA...')
            from ml.models.arima_model import ARIMAForecaster
            arima = ARIMAForecaster(use_auto_order=True, max_p=2, max_q=2)
            arima.fit(train_df)
            arima.save(arima_path)
            try:
                m = arima.evaluate(test_df)
                all_metrics['arima'] = {k: float(v) if not isinstance(v, str) else v for k, v in m.items()}
                print(f'✅ ARIMA saved - MAPE: {m.get("mape", "N/A")}')
            except:
                all_metrics['arima'] = {"mape": None, "rmse": None}
                print('✅ ARIMA saved')
        
        # Train & Evaluate Prophet
        if not os.path.exists(prophet_path):
            print(f'Training Prophet...')
            from ml.models.prophet_model import ProphetForecaster
            prophet = ProphetForecaster()
            prophet.fit(train_df)
            prophet.save(prophet_path)
            try:
                m = prophet.evaluate(test_df)
                all_metrics['prophet'] = {k: float(v) if not isinstance(v, str) else v for k, v in m.items()}
                print(f'✅ Prophet saved - MAPE: {m.get("mape", "N/A")}')
            except:
                all_metrics['prophet'] = {"mape": None, "rmse": None}
                print('✅ Prophet saved')
        
        # Train & Evaluate ARIMAX
        if not os.path.exists(arimax_path):
            print(f'Training ARIMAX...')
            from ml.models.arimax_model import ARIMAXForecaster
            arimax = ARIMAXForecaster()
            arimax.fit(train_df)
            arimax.save(arimax_path)
            try:
                m = arimax.evaluate(test_df)
                all_metrics['arimax'] = {k: float(v) if not isinstance(v, str) else v for k, v in m.items()}
                print(f'✅ ARIMAX saved - MAPE: {m.get("mape", "N/A")}')
            except:
                all_metrics['arimax'] = {"mape": None, "rmse": None}
                print('✅ ARIMAX saved')
        
        # Save metrics
        with open(metrics_path, 'w') as f:
            json.dump(all_metrics, f, indent=2)
        print(f'📊 Metrics saved ({len(all_metrics)} models)')
        
        print('🎉 Training complete')
    else:
        print(f'❌ Not enough data: {len(rates)} rows (need 30+)')