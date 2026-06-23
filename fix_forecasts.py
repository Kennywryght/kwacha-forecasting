# Fix forecasts.py bugs
with open('backend/api/routes/forecasts.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: forecast() -> predict()
content = content.replace(
    'raw = model.forecast(horizon)',
    'raw = model.predict(horizon)'
)

# Fix 2: Date comparison
old = '''clean_dates = [_safe_date(d) for d in dates]
    filtered = [
        (d, p, l, u)
        for d, p, l, u in zip(clean_dates, predicted, lower, upper)
        if d >= start_date
    ]'''

new = '''clean_dates = [_safe_date(d) for d in dates]
    start_d = _safe_date(start_date) if not isinstance(start_date, date) else start_date
    filtered = [
        (d, p, l, u)
        for d, p, l, u in zip(clean_dates, predicted, lower, upper)
        if d >= start_d
    ]'''

content = content.replace(old, new)

with open('backend/api/routes/forecasts.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed forecasts.py')
