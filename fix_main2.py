# Fix main.py to add ARIMAX training and CSV loading

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add ARIMAX training after Prophet
old = "prophet.save(prophet_path)\n            logger.info('Prophet trained and saved')"
new = """prophet.save(prophet_path)
            logger.info('Prophet trained and saved')
        
        arimax_path = os.path.join(artifacts_dir, 'arimax.pkl')
        if not os.path.exists(arimax_path):
            logger.info('Training ARIMAX...')
            from ml.models.arimax_model import ARIMAXForecaster
            arimax = ARIMAXForecaster()
            arimax.fit(df)
            arimax.save(arimax_path)
            logger.info('ARIMAX trained and saved')"""

content = content.replace(old, new)

# Update data loading to keep all columns
old_filter = "df = df[['date', 'rate']].dropna()"
new_filter = "df = df.dropna(subset=[date_col, rate_col])"
content = content.replace(old_filter, new_filter)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated main.py with ARIMAX training')
