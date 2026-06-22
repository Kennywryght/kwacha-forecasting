import os

# Read current main.py
with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Auto-training function
auto_train = '''
def auto_train_models():
    import os
    from core.logging_config import get_logger
    logger = get_logger(__name__)
    
    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ml', 'artifacts'))
    os.makedirs(artifacts_dir, exist_ok=True)
    
    arima_path = os.path.join(artifacts_dir, 'arima.pkl')
    prophet_path = os.path.join(artifacts_dir, 'prophet.pkl')
    
    if os.path.exists(arima_path) and os.path.exists(prophet_path):
        logger.info('Models already exist')
        return
    
    logger.info('Training models - this will take a few minutes...')
    
    try:
        from ml.pipeline.loader import load_data
        df = load_data()
        logger.info(f'Loaded {len(df)} rows for training')
        
        if len(df) < 30:
            logger.warning(f'Not enough data: {len(df)} rows')
            return
        
        if not os.path.exists(arima_path):
            logger.info('Training ARIMA...')
            from ml.models.arima_model import ARIMAForecaster
            arima = ARIMAForecaster()
            arima.fit(df)
            arima.save(arima_path)
            logger.info('ARIMA trained and saved')
        
        if not os.path.exists(prophet_path):
            logger.info('Training Prophet...')
            from ml.models.prophet_model import ProphetForecaster
            prophet = ProphetForecaster()
            prophet.fit(df)
            prophet.save(prophet_path)
            logger.info('Prophet trained and saved')
            
    except Exception as e:
        logger.error(f'Auto-training failed: {e}')
        import traceback
        traceback.print_exc()
'''

# Insert before def load_models
if 'def load_models():' in content:
    content = content.replace('def load_models():', auto_train + '\n\ndef load_models():')
    print('Inserted auto_train_models function')
else:
    print('ERROR: def load_models() not found!')

# Add call in startup
if 'logger.info("Database tables ready")' in content or "logger.info('Database tables ready')" in content:
    content = content.replace(
        'logger.info("Database tables ready")',
        'logger.info("Database tables ready")\n    auto_train_models()'
    )
    content = content.replace(
        "logger.info('Database tables ready')",
        "logger.info('Database tables ready')\n    auto_train_models()"
    )
    print('Added auto_train_models() call')
else:
    print('ERROR: Database tables ready not found!')

# Write back
with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('main.py updated successfully')
