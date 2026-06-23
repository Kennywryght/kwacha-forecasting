import os, sys
sys.path.insert(0, '.')

# Read the arima_model.py
with open('backend/ml/models/arima_model.py', 'r') as f:
    content = f.read()

# Fix: When d > 0, use trend='n' (no trend) to avoid the error
content = content.replace(
    "trend=self.trend,",
    "trend='n' if self.order[1] > 0 else self.trend,"
)

with open('backend/ml/models/arima_model.py', 'w') as f:
    f.write(content)

print('Fixed ARIMA trend parameter')
