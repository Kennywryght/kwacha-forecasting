import os, sys
sys.path.insert(0, 'backend')
# Already in backend directory

from db.database import SessionLocal
from db.models import ExchangeRate
from datetime import date, timedelta
import numpy as np
from sqlalchemy import func

db = SessionLocal()

# Delete old synthetic data from Oct 2024 onwards
db.query(ExchangeRate).filter(
    ExchangeRate.date >= '2024-10-01',
    ExchangeRate.source.in_(['projection', 'synthetic', 'trend_projection', 'realistic_projection'])
).delete(synchronize_session=False)
db.commit()
print('Deleted old synthetic data')

# Get the anchor - last real rate before Oct 2024
last_real = db.query(ExchangeRate).filter(
    ExchangeRate.date < '2024-10-01'
).order_by(ExchangeRate.date.desc()).first()

anchor_rate = float(last_real.rate) if last_real else 1733.67
print(f'Anchor rate: {anchor_rate}')

# Realistic monthly data based on your research
# Format: (year, month, typical_rate, range_low, range_high, description)
monthly_data = [
    (2024, 10, 1733, 1718, 1747, "Stable, central bank managed"),
    (2024, 11, 1733, 1716, 1735, "Extended flat stretches"),
    (2024, 12, 1733, 1718, 1742, "Neutral, holiday stability"),
    (2025, 1,  1733, 1731, 1735, "Tight control, 0.01% volatility"),
    (2025, 2,  1734, 1732, 1761, "Spike to 1761.89 on Feb 2, then flat"),
    (2025, 3,  1734, 1731, 1736, "Stabilized after Feb spike"),
    (2025, 4,  1734, 1731, 1742, "Peg-like conditions"),
    (2025, 5,  1734, 1731, 1742, "Firmly stabilized"),
    (2025, 6,  1751, 1731, 1751, "Anchored at 1751 by RBM"),
    (2025, 7,  1751, 1731, 1751, "Rigidly stabilized at 1751"),
    (2025, 8,  1735, 1713, 1739, "Brief low of 1713, then 1734-1736"),
    (2025, 9,  1750, 1731, 1751, "Capped at ~1750 for quarter-end"),
    (2025, 10, 1750, 1731, 1751, "Official 1749.95, parallel 1937"),
    (2025, 11, 1750, 1731, 1751, "Unaltered from October"),
    (2025, 12, 1734, 1731, 1751, "Closed at 1733.67"),
    (2026, 1,  1749, 1721, 1746, "Middle rate 1749.35"),
    (2026, 2,  1734, 1721, 1746, "Middle rate 1733.91"),
    (2026, 3,  1735, 1732, 1737, "Average 1734.60, tight range"),
    (2026, 4,  1750, 1730, 1751, "Average 1749.68"),
    (2026, 5,  1737, 1731, 1737, "Average 1737.53, 0% devaluation"),
    (2026, 6,  1734, 1732, 1737, "Middle rate 1733.67, lending rate 20.40%"),
]

current_date = date(2024, 10, 1)
today = date.today()
added = 0

for year, month, typical, low, high, desc in monthly_data:
    # Calculate days in this month
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    
    days_in_month = (next_month - date(year, month, 1)).days
    
    # Current rate for this month
    current_rate = typical
    
    for day in range(days_in_month):
        gen_date = date(year, month, 1) + timedelta(days=day)
        
        if gen_date > today:
            break
        
        if gen_date < current_date:
            continue
        
        # Skip weekends (no trading)
        if gen_date.weekday() >= 5:
            continue
        
        # Special case: Feb 2, 2025 spike
        if gen_date == date(2025, 2, 2):
            current_rate = 1761.89
        # Special case: Aug 3, 2025 low
        elif gen_date == date(2025, 8, 3):
            current_rate = 1713.00
        else:
            # Very small daily variation (0.00-0.01% as per research)
            # Most days have ZERO change
            if np.random.random() < 0.15:  # Only 15% of days have any change
                change = np.random.uniform(-0.5, 0.5)
                current_rate += change
            
            # Clamp to monthly range
            current_rate = max(low, min(high, current_rate))
            current_rate = round(current_rate, 2)
        
        existing = db.query(ExchangeRate).filter(
            ExchangeRate.date == gen_date
        ).first()
        
        if not existing:
            db.add(ExchangeRate(
                date=gen_date,
                rate=current_rate,
                open_rate=current_rate,
                high_rate=round(current_rate * 1.001, 2),
                low_rate=round(current_rate * 0.999, 2),
                source='research_based'
            ))
            added += 1
    
    if date(year, month, 1) > today:
        break

db.commit()

# Show results
total = db.query(ExchangeRate).count()
latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()

print(f'\nAdded {added} research-based data points')
print(f'Total database: {total} rows')
print(f'Latest: {latest.date} = {latest.rate}')

# Show monthly averages
print('\nMonthly averages:')
for year, month, typical, low, high, desc in monthly_data:
    month_data = db.query(ExchangeRate).filter(
        func.extract('year', ExchangeRate.date) == year,
        func.extract('month', ExchangeRate.date) == month,
        ExchangeRate.source == 'research_based'
    ).all()
    if month_data:
        avg = np.mean([float(r.rate) for r in month_data])
        mn = np.min([float(r.rate) for r in month_data])
        mx = np.max([float(r.rate) for r in month_data])
        print(f'  {year}-{month:02d}: avg={avg:.2f}  [{mn:.2f}-{mx:.2f}]  {desc}')

db.close()
print('\nDone!')
