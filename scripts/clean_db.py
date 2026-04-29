from db.database import SessionLocal
from db.models import Forecast, ExchangeRate
from datetime import date

db = SessionLocal()

try:
    # 🚨 Remove bad forecasts
    db.query(Forecast).filter(Forecast.target_date > date.today()).delete()
    db.query(Forecast).filter(Forecast.target_date < date(2013, 1, 1)).delete()

    # 🚨 Remove interpolated/fake rates if needed
    db.query(ExchangeRate).filter(ExchangeRate.is_interpolated == True).delete()

    db.commit()
    print("✅ Database cleaned successfully")

except Exception as e:
    db.rollback()
    print("❌ Error:", e)

finally:
    db.close()