import os, sys
sys.path.insert(0, '.')

# Read forecasts.py
with open('backend/api/routes/forecasts.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the ARIMAX retrain section and fix it
old_arimax = '''if "arimax" in _models:
                try:
                    logger.info("  Retraining ARIMAX...")
                    _models["arimax"].fit(rates)
                    logger.info("  ✅ ARIMAX retrained")
                except Exception as e:
                    logger.error(f"  ❌ ARIMAX retraining failed: {e}")'''

new_arimax = '''if "arimax" in _models:
                try:
                    logger.info("  Retraining ARIMAX...")
                    # Add engineered features for ARIMAX
                    from ml.pipeline.feature_engineer import engineer_features
                    rates_eng = engineer_features(rates.copy(), verbose=False)
                    _models["arimax"].fit(rates_eng)
                    logger.info("  ✅ ARIMAX retrained")
                except Exception as e:
                    logger.error(f"  ❌ ARIMAX retraining failed: {e}")'''

if old_arimax in content:
    content = content.replace(old_arimax, new_arimax)
    print('Fixed ARIMAX retrain - added feature engineering')
else:
    print('Could not find ARIMAX retrain block')
    # Try alternate pattern
    old = '_models["arimax"].fit(rates)'
    new = 'from ml.pipeline.feature_engineer import engineer_features; _models["arimax"].fit(engineer_features(rates.copy(), verbose=False))'
    if old in content:
        content = content.replace(old, new)
        print('Fixed ARIMAX retrain (alternate method)')

with open('backend/api/routes/forecasts.py', 'w', encoding='utf-8') as f:
    f.write(content)
