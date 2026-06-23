import os, sys
sys.path.insert(0, 'backend')
os.chdir('backend')

from db.database import SessionLocal
from db.models import ExchangeRate
from datetime import date, timedelta
import numpy as np
import pandas as pd

db = SessionLocal()

# Get last 90 days of real data to analyze trend
real_data = db.query(ExchangeRate).filter(
    ExchangeRate.date >= '2024-08-19'
).order_by(ExchangeRate.date.asc()).all()

if len(real_data) < 30:
    print("Not enough real data for trend analysis")
    db.close()
    exit()

# Extract rates and dates
dates = [r.date for r in real_data]
rates = [float(r.rate) for r in real_data]

# Calculate trend metrics from real data
rates_series = pd.Series(rates)
trend = rates_series.diff().mean()  # Average daily change
volatility = rates_series.diff().std()  # Standard deviation of changes
last_rate = rates[-1]
last_date = dates[-1]

print(f"Last real date: {last_date}")
print(f"Last real rate: {last_rate:.2f}")
print(f"Avg daily change: {trend:.4f}")
print(f"Daily volatility: {volatility:.4f}")
print(f"Monthly trend: {trend * 30:.2f}")

# Also detect if there was a recent devaluation/jump
recent_change = rates_series.iloc[-30:].diff().mean()
print(f"Recent 30-day trend: {recent_change:.4f}")

# Use the more conservative trend
projection_trend = recent_change if abs(recent_change) < abs(trend) * 3 else trend

# Generate realistic data from last_date+1 to today
current_date = last_date + timedelta(days=1)
today = date.today()
current_rate = last_rate
added = 0
projected_rates = []

# Add some realistic patterns:
# - Weekday variations
# - Occasional small jumps
# - Mean-reverting tendency
days_since_real = (today - last_date).days

for i in range(days_since_real):
    if current_date > today:
        break
    
    # Skip weekends (no trading)
    if current_date.weekday() < 5:
        # Base: apply trend
        base_change = projection_trend
        
        # Add day-of-week effect (Mondays often have bigger moves)
        if current_date.weekday() == 0:
            base_change *= 1.2
        
        # Add volatility with slight mean reversion
        random_component = np.random.normal(0, volatility * 0.5)
        
        # Mean reversion: if we've drifted too far from trend, pull back
        if len(projected_rates) > 20:
            recent_projected = projected_rates[-20:]
            drift = current_rate - (last_rate + projection_trend * len(projected_rates))
            reversion = -drift * 0.05  # 5% mean reversion
        else:
            reversion = 0
        
        # Combine all components
        daily_change = base_change + random_component + reversion
        
        # Limit extreme daily moves (max 2% daily change)
        daily_change = max(min(daily_change, current_rate * 0.02), -current_rate * 0.02)
        
        current_rate += daily_change
        current_rate = max(current_rate, 100)  # Floor
        
        # Round to 2 decimal places (standard forex)
        current_rate = round(current_rate, 2)
        
        # Occasionally add small intraday variation pattern
        if np.random.random() < 0.1:  # 10% chance of a small jump
            current_rate += np.random.uniform(-1, 1)
            current_rate = round(current_rate, 2)
        
        projected_rates.append(current_rate)
        
        # Check if date exists
        existing = db.query(ExchangeRate).filter(
            ExchangeRate.date == current_date
        ).first()
        
        if not existing:
            db.add(ExchangeRate(
                date=current_date,
                rate=current_rate,
                open_rate=round(current_rate * (1 + np.random.uniform(-0.001, 0.001)), 2),
                high_rate=round(current_rate * (1 + abs(np.random.uniform(0, 0.003))), 2),
                low_rate=round(current_rate * (1 - abs(np.random.uniform(0, 0.003))), 2),
                source='trend_projection'
            ))
            added += 1
    
    current_date += timedelta(days=1)

db.commit()

# Print summary
print(f"\nAdded {added} days of projected data")
print(f"Date range: {last_date + timedelta(days=1)} to {today}")
print(f"Final projected rate: {current_rate:.2f}")
print(f"Total change from real: {current_rate - last_rate:.2f} MWK")
print(f"Percent change: {((current_rate - last_rate) / last_rate * 100):.2f}%")

# Verify
total = db.query(ExchangeRate).count()
latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
print(f"\nTotal records: {total}")
print(f"Latest date: {latest.date}")
print(f"Latest rate: {latest.rate}")

db.close()
