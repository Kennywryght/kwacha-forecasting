with open('frontend/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the TrustChart usage and check what's passed
import re
matches = re.findall(r'<TrustChart[^>]*>', content)
for m in matches:
    print(f'Found: {m}')

# Check if it's using forecast7d or forecasts
if 'forecast7d || forecasts' in content:
    print('Using forecast7d || forecasts')
elif 'forecasts={forecast7d' in content:
    print('Using forecast7d')
elif 'forecasts={forecasts}' in content:
    print('Using forecasts (from useDashboardData)')
