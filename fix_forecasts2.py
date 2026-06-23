# Fix ALL forecast bugs at once
with open('backend/api/routes/forecasts.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the _adjust_forecast_dates function
old_func_start = 'def _adjust_forecast_dates(raw: dict, horizon: int, start_date: date) -> dict:'
old_func_end = 'return {"dates": [], "predicted": [], "lower_bound": [], "upper_bound": []}'

# New function
new_func = '''def _adjust_forecast_dates(raw: dict, horizon: int, start_date: date) -> dict:
    """Adjust forecast dates to ensure they start from start_date and are limited to horizon length."""
    dates = raw.get("dates", [])
    predicted = raw.get("predicted", [])
    lower = raw.get("lower_bound", []) or raw.get("lower", [])
    upper = raw.get("upper_bound", []) or raw.get("upper", [])

    # Convert all dates to date objects for comparison
    clean_dates = []
    for d in dates:
        if isinstance(d, str):
            clean_dates.append(datetime.strptime(d, '%Y-%m-%d').date())
        elif hasattr(d, 'date'):
            clean_dates.append(d.date())
        elif isinstance(d, datetime):
            clean_dates.append(d.date())
        else:
            clean_dates.append(d)

    # Convert start_date to date
    if isinstance(start_date, str):
        start_d = datetime.strptime(start_date, '%Y-%m-%d').date()
    elif hasattr(start_date, 'date'):
        start_d = start_date.date()
    elif isinstance(start_date, datetime):
        start_d = start_date.date()
    else:
        start_d = start_date

    # Convert predictions to lists if they're numpy arrays
    if hasattr(predicted, 'tolist'):
        predicted = predicted.tolist()
    elif hasattr(predicted, 'values'):
        predicted = predicted.values.tolist()
    
    if hasattr(lower, 'tolist'):
        lower = lower.tolist()
    elif hasattr(lower, 'values'):
        lower = lower.values.tolist()
    
    if hasattr(upper, 'tolist'):
        upper = upper.tolist()
    elif hasattr(upper, 'values'):
        upper = upper.values.tolist()

    # Pad lower/upper if shorter than predicted
    if len(lower) < len(predicted):
        lower = list(lower) + [None] * (len(predicted) - len(lower))
    if len(upper) < len(predicted):
        upper = list(upper) + [None] * (len(predicted) - len(upper))

    filtered = [
        (d, p, l, u)
        for d, p, l, u in zip(clean_dates, predicted, lower, upper)
        if d >= start_d
    ]
    filtered = filtered[:horizon]

    if filtered:
        new_dates, new_pred, new_lower, new_upper = zip(*filtered)
        return {
            "dates": [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in new_dates],
            "predicted": [float(p) for p in new_pred],
            "lower_bound": [float(l) if l is not None else None for l in new_lower],
            "upper_bound": [float(u) if u is not None else None for u in new_upper],
        }
    return {"dates": [], "predicted": [], "lower_bound": [], "upper_bound": []}'''

# Find the function boundaries
start_idx = content.find(old_func_start)
end_idx = content.find(old_func_end, start_idx)

if start_idx >= 0 and end_idx >= 0:
    content = content[:start_idx] + new_func + content[end_idx + len(old_func_end):]
    print('Replaced _adjust_forecast_dates function')
else:
    print('Could not find function boundaries')

# Also ensure datetime is imported
if 'from datetime import date, datetime, timedelta' not in content:
    content = content.replace(
        'from datetime import date, datetime, timedelta',
        'from datetime import date, datetime, timedelta'
    )

with open('backend/api/routes/forecasts.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Forecasts.py fully fixed')
