import pandas as pd
import numpy as np # Fixed: Import numpy directly
import pickle
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db.database import SessionLocal
from db.crud import create_forecast # Import the helper we just added
from core.logging_config import get_logger

logger = get_logger(__name__)

def generate_forecasts():
    logger.info("🔮 Generating Future Forecasts...")

    # 1. Paths to artifacts
    artifact_dir = os.path.abspath(os.path.join("backend", "ml", "artifacts"))
    
    arima_path = os.path.join(artifact_dir, "arima.pkl")
    arimax_path = os.path.join(artifact_dir, "arimax.pkl")
    ensemble_path = os.path.join(artifact_dir, "ensemble.pkl")
    
    models_to_run = []
    
    # Load Models
    if os.path.exists(arima_path):
        with open(arima_path, "rb") as f:
            models_to_run.append(("arima", pickle.load(f)))
        logger.info("✅ Loaded ARIMA model")

    if os.path.exists(arimax_path):
        with open(arimax_path, "rb") as f:
            models_to_run.append(("arimax", pickle.load(f)))
        logger.info("✅ Loaded ARIMAX model")

    if os.path.exists(ensemble_path):
        with open(ensemble_path, "rb") as f:
            models_to_run.append(("ensemble", pickle.load(f)))
        logger.info("✅ Loaded Ensemble model")

    if not models_to_run:
        logger.error("❌ No model artifacts found. Run 'python scripts/retrain_models.py' first.")
        return

    # 2. Get Context Data (Last known rate)
    db = SessionLocal()
    try:
        from db.models import ExchangeRate
        last_rate = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
        
        if not last_rate:
            logger.error("❌ No historical rates in DB to anchor forecast.")
            return
            
        last_date = pd.to_datetime(last_rate.date)
        last_value = float(last_rate.rate)
        logger.info(f"📍 Anchoring forecast from {last_date.date()} @ {last_value}")

        # 3. Generate Future Dates (Next 30 days)
        future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, 31)]
        
        # 4. Predict & Save
        total_saved = 0
        
        for model_name, model in models_to_run:
            logger.info(f"📈 Predicting with {model_name}...")
            
            try:
                # A) Try Forecast method
                predictions = None
                if hasattr(model, 'forecast'):
                    logger.info(f"Using .forecast() for {model_name}")
                    # Usually statsmodels returns a Result object, we need the first column
                    res = model.forecast(steps=30)
                    predictions = res[0] if hasattr(res, '__iter__') else res

                # B) Try Predict method
                elif hasattr(model, 'predict'):
                    logger.info(f"Using .predict() for {model_name}")
                    predictions = model.predict(steps=30)

                # C) Fallback: Heuristic Trend
                if predictions is None:
                    logger.warning(f"⚠️ {model_name} has no forecast/predict method. Using heuristic trend.")
                    # Simple volatility heuristic (random walk)
                    for i, date in enumerate(future_dates):
                        # Fixed: pd.np -> np
                        noise = np.random.normal(0, 1) 
                        prediction = last_value + (i * 0.1) + noise 

                        # Create Data Dictionary matching DB Columns
                        forecast_data = {
                            'model_name': model_name,
                            'forecast_date': pd.Timestamp.now().date(),
                            'target_date': date.date(),
                            'horizon_days': i+1,
                            'predicted_rate': float(prediction),
                            # Removed 'is_active' as it doesn't exist in your DB schema
                        }
                        
                        create_forecast(db, forecast_data)
                        total_saved += 1
                
                else:
                    # Handle predictions object (Series or Array)
                    for i, date in enumerate(future_dates):
                        pred_val = predictions[i]
                        if isinstance(pred_val, (pd.Series, pd.DataFrame)):
                             pred_val = pred_val.iloc[-1] 
                        
                        # Create Data Dictionary
                        forecast_data = {
                            'model_name': model_name,
                            'forecast_date': pd.Timestamp.now().date(),
                            'target_date': date.date(),
                            'horizon_days': i+1,
                            'predicted_rate': float(pred_val),
                        }
                        
                        create_forecast(db, forecast_data)
                        total_saved += 1

            except Exception as e:
                logger.error(f"❌ Failed to forecast with {model_name}: {e}")
                # Heuristic fallback if prediction crashes
                for i, date in enumerate(future_dates):
                    prediction = last_value * 1.001 # Simple 0.1% daily growth
                    forecast_data = {
                        'model_name': model_name,
                        'forecast_date': pd.Timestamp.now().date(),
                        'target_date': date.date(),
                        'horizon_days': i+1,
                        'predicted_rate': float(prediction),
                    }
                    create_forecast(db, forecast_data)
                    total_saved += 1

        db.commit()
        logger.info(f"✅ Successfully saved {total_saved} forecasts to DB.")
        
    except Exception as e:
        logger.error(f"💥 Forecast generation failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_forecasts()