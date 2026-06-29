# KwachaCast User Guide

## Getting Started

### Access the Dashboard
1. Open your browser and go to: [kwachacast.vercel.app](https://kwachacast.vercel.app)
2. If this is your first visit, you'll see an empty dashboard
3. Click the **"Generate Forecasts"** button to create today's predictions
4. Wait a few seconds for the models to generate forecasts
5. The dashboard will refresh automatically

### Install on Your Phone (PWA)
1. Open the dashboard in Chrome on your Android phone
2. Tap the three-dot menu (⋮) in the top-right corner
3. Select **"Add to Home Screen"**
4. Name it "KwachaCast" and tap **Add**
5. The app will appear on your home screen — no app store needed
6. Works offline once loaded

---

## Understanding the Dashboard

### KPI Cards (Top)
Shows the most important numbers at a glance:
- **Current rate**: Today's MWK/USD exchange rate
- **Next day**: Tomorrow's predicted rate
- **7 days**: Predicted rate in one week
- **30 days**: Predicted rate in one month

Each prediction shows a percentage change:
- ↗ **Red** = Kwacha weakening (rate going up)
- ↘ **Green** = Kwacha strengthening (rate going down)

### Forecast Outlook (Chart)
Shows predicted exchange rates across different timeframes:
- **Green line**: Next day forecast
- **Blue line**: 7-day forecast
- **Yellow line**: 30-day forecast
- **Vertical lines on dots**: 95% confidence interval (where we expect the rate to fall)
- **Longer lines** = more uncertainty

### What You Should Do
Actionable advice based on the forecast:
- **Stable** (green): No action needed
- **Weakening** (red): Consider buying USD now
- **Strengthening** (green): Consider holding Kwacha or converting USD

### How This Affects You
Personalized guidance for different situations:
- Shopping for imported goods
- Paying school fees
- Running a business
- Receiving money from abroad

### Historical Trends
Shows past exchange rates for context:
- **Green line**: Actual historical rates
- **Yellow dotted line**: Our past forecasts overlaid

---

## Refreshing Forecasts

Forecasts are generated daily, but you can manually refresh:
1. Click the **"Refresh"** button in the top-right corner
2. Wait for generation to complete
3. The dashboard updates automatically

---

## Exporting Data

### Export Forecasts
1. Click the **"Export"** button in the top-right corner
2. A CSV file downloads with:
   - Target date
   - Predicted rate
   - Lower bound (95% confidence)
   - Upper bound (95% confidence)

### API Access
For programmatic access, use the API:
- Documentation: [kwachacast-api.onrender.com/docs](https://kwachacast-api.onrender.com/docs)
- Example: `GET /api/v1/forecasts/latest?horizon=7&model=ensemble`

---

## Frequently Asked Questions

### How accurate are the forecasts?
Our models achieve 0.30% MAPE — predictions are typically within 5 MWK of the actual rate. The accuracy card on the dashboard shows real-time performance.

### How often are forecasts updated?
Forecasts are generated daily. Click "Refresh" to get the latest predictions.

### What does "Strengthening" mean?
The Kwacha is gaining value. You need fewer Kwacha to buy 1 USD.

### What does "Weakening" mean?
The Kwacha is losing value. You need more Kwacha to buy 1 USD.

### Where does the data come from?
Exchange rates from the Reserve Bank of Malawi and live currency APIs. Updated daily.

### Can I trust these forecasts for large transactions?
Forecasts are informational only. While our accuracy is high (0.30% error), exchange rates can be affected by unexpected events. Always consider multiple sources for significant financial decisions.

### Why do confidence intervals get wider for 30-day forecasts?
Uncertainty compounds over time. We're more confident about tomorrow's rate than next month's rate. The wider bands honestly communicate this increasing uncertainty.

### How do I report an issue?
Visit our GitHub repository: [github.com/Kennywryght/kwacha-forecasting](https://github.com/Kennywryght/kwacha-forecasting)