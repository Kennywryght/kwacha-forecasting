# Add ARIMAX to pretrain.py
with open('backend/pretrain.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = "print('Prophet saved')"
new = """print('Prophet saved')
    
    print('Training ARIMAX...')
    from ml.models.arimax_model import ARIMAXForecaster
    arimax = ARIMAXForecaster()
    arimax.fit(df)
    arimax.save('ml/artifacts/arimax.pkl')
    print('ARIMAX saved')"""

content = content.replace(old, new)

with open('backend/pretrain.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Added ARIMAX to pretrain')
