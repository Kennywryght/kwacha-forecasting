# KwachaCast API Reference

**Base URL**: `https://kwachacast-api.onrender.com/api/v1`  
**Interactive Docs**: `https://kwachacast-api.onrender.com/docs`  
**OpenAPI Spec**: `https://kwachacast-api.onrender.com/openapi.json`

---

## Exchange Rates

### GET /rates/latest
Returns the most recent exchange rate.

**Response:**
```json
{
  "date": "2026-06-29",
  "rate": 1735.50,
  "source": "live_api"
}

GET /rates/history
Returns historical rates within a date range.

Parameters:

Parameter	Type	Required	Description
start_date	string	Yes	Start date (YYYY-MM-DD)
end_date	string	Yes	End date (YYYY-MM-DD)
Response:
{
  "data": [
    {"date": "2026-06-01", "rate": 1730.00},
    {"date": "2026-06-02", "rate": 1731.50}
  ],
  "total": 2,
  "start_date": "2026-06-01",
  "end_date": "2026-06-02"
}

GET /rates/stats
Returns statistical summary of recent rates.

Response:{
  "current": 1735.50,
  "min_7d": 1730.00,
  "max_7d": 1740.00,
  "change_7d": 2.50,
  "change_pct_7d": 0.14,
  "avg_30d": 1733.25
}

GET /rates/alerts
Returns rate alerts based on thresholds.

GET /rates/export
Export rates as CSV or JSON.

Parameters:

Parameter	Type	Default	Description
format	string	json	Output format (json or csv)
Forecasts
GET /forecasts/status
Check if today's forecasts are available.

Parameters:

Parameter	Type	Default	Description
horizon	integer	7	Forecast horizon (1, 7, or 30)
Response:
{
  "horizon_days": 7,
  "is_fresh": true,
  "forecast_date": "2026-06-29",
  "loaded_models": ["arima", "arimax", "prophet", "xgboost", "lightgbm"],
  "status": "ready"
}

GET /forecasts/latest
Get the latest forecasts for a specific model.

Parameters:

Parameter	Type	Default	Description
model	string	ensemble	Model name
horizon	integer	7	Forecast horizon
Response:
{
  "model_name": "arimax",
  "forecast_date": "2026-06-29",
  "horizon_days": 7,
  "forecasts": [
    {
      "target_date": "2026-06-30",
      "predicted_rate": 1736.20,
      "lower_bound": 1731.00,
      "upper_bound": 1741.40
    }
  ]
}
GET /forecasts/all
Get forecasts from all loaded models.

Parameters:

Parameter	Type	Default	Description
horizon	integer	7	Forecast horizon
GET /forecasts/1-day
Get the latest 1-day forecast (ARIMAX).

GET /forecasts/7-day
Get the latest 7-day forecasts (ARIMAX).

GET /forecasts/30-day
Get the latest 30-day forecasts (ARIMAX).

GET /forecasts/summary
Get forecast endpoints for all horizons.

Response:
{
  "current_rate": 1735.50,
  "current_date": "2026-06-29",
  "forecasts": {
    "1_day": {
      "predicted_rate": 1735.80,
      "target_date": "2026-06-30",
      "lower_bound": 1733.50,
      "upper_bound": 1738.10
    },
    "7_day": {
      "predicted_rate": 1738.00,
      "target_date": "2026-07-06",
      "lower_bound": 1730.00,
      "upper_bound": 1746.00
    },
    "30_day": {
      "predicted_rate": 1745.00,
      "target_date": "2026-07-29",
      "lower_bound": 1725.00,
      "upper_bound": 1765.00
    }
  }
}
POST /forecasts/generate
Trigger forecast generation for all models.

Parameters:

Parameter	Type	Default	Description
horizon	integer	7	Forecast horizon
Response:
{
  "status": "generating",
  "message": "Generation started for horizon=7.",
  "generated_at": "2026-06-29"
}
POST /forecasts/retrain
Retrain all models with latest data.

GET /forecasts/accuracy
Compare past forecasts against actual rates.

Response:
{
  "model": "arimax",
  "forecast_date": "2026-06-22",
  "comparisons": [
    {
      "target_date": "2026-06-23",
      "predicted": 1735.00,
      "actual": 1735.50,
      "error_mwk": 0.50,
      "error_pct": 0.0288,
      "within_range": true
    }
  ],
  "avg_error_mwk": 0.50,
  "avg_error_pct": 0.0288,
  "within_range_pct": 100.0
}

GET /forecasts/quick
One-line forecast summary for bots and notifications.

Response:
{
  "message": "MWK/USD: 1,735.50 | 7-day: 1,738.00 (↗ 2.50)",
  "current_rate": 1735.50,
  "forecast_7d": 1738.00,
  "change_mwk": 2.50,
  "change_pct": 0.14
}

GET /forecasts/export
Export forecasts as CSV or JSON.

GET /forecasts/generation-status
Check current generation progress.

Models
GET /models/performance
Get performance metrics for all trained models.

GET /models/health
Get health status of all models.

Pipeline
POST /pipeline/retrain
Trigger full pipeline retraining.

GET /pipeline/status
Get current pipeline status.

---

### **File 3: `docs/model_card.md`**

```markdown
# Model Card: KwachaCast Ensemble

## Model Details

- **Name**: KwachaCast Ensemble Forecaster
- **Version**: 1.0.0
- **Type**: Weighted ensemble of 5 forecasting models
- **Training Date**: June 2026
- **Training Data**: 4,000+ daily MWK/USD rates (2013–2024)
- **Update Frequency**: Daily refit, weekly full retraining

---

## Intended Use

### Primary Use
Short to medium-term MWK/USD exchange rate forecasting for:
- Import/export planning
- Personal finance decisions (remittances, school fees)
- Business budgeting
- Currency conversion timing

### Out of Scope
- Intraday trading
- Other currency pairs
- Long-term investment decisions (>3 months)
- Financial advice (informational only)

### Users
- Business owners in Malawi
- Individuals receiving/sending money abroad
- Students paying international fees
- Importers and exporters
- Policy researchers

---

## Performance Metrics

Evaluated on 15% held-out test set (2024–2026):

| Metric | Value | Interpretation |
|--------|-------|----------------|
| MAPE | 0.30% | Average prediction error of 0.30% |
| RMSE | 4.88 MWK | Typical error of ~5 MWK |
| R² | 0.991 | Explains 99.1% of rate variance |
| Directional Accuracy | 78% | Correct direction 78% of the time |

### Performance by Horizon

| Horizon | MAPE | RMSE | Confidence Interval Width |
|---------|------|------|---------------------------|
| 1 day | 0.05% | 0.87 MWK | ±1.7 MWK |
| 7 days | 0.20% | 3.47 MWK | ±6.8 MWK |
| 30 days | 0.65% | 11.28 MWK | ±22.1 MWK |

*Accuracy decreases and uncertainty increases with longer horizons.*

---

## Training Data

- **Source**: Reserve Bank of Malawi
- **Period**: January 2013 – June 2024 (training), July 2024 – June 2026 (testing)
- **Size**: 4,000+ training records, 700+ test records
- **Frequency**: Daily (business days)
- **Preprocessing**: Forward-fill for missing values, removal of duplicate dates
- **Features**: 42 engineered features (see methodology documentation)

---

## Limitations

1. **Managed exchange rate assumption**: Models are optimized for Malawi's managed float regime. Free-floating scenarios or structural breaks (devaluations) may temporarily reduce accuracy.

2. **Exogenous variable forecasting**: Future values of inflation, interest rates, and other macroeconomic indicators are assumed to remain at current levels. This is a simplification that may affect longer-horizon predictions.

3. **Data quality**: Historical data from 2013–2016 may have gaps or interpolation artifacts that affect model training.

4. **Black swan events**: The models cannot predict unexpected events (natural disasters, political crises, sudden policy changes).

5. **Horizon degradation**: Accuracy decreases as forecast horizon increases. 30-day forecasts should be used with appropriate caution.

6. **Single currency pair**: Models are trained only on MWK/USD. Performance on other currency pairs is unknown.

---

## Ethical Considerations

### Transparency
- All model metrics are publicly available
- Confidence intervals are provided with every forecast
- Past forecast accuracy is tracked and displayed

### Fairness
- Forecasts are equally accessible to all users
- No user-specific pricing or feature gating
- API is free and open

### Accountability
- Clear disclaimer: forecasts are informational, not financial advice
- Limitations are documented and accessible
- Users are encouraged to consider multiple information sources

### Privacy
- No user data is collected or stored
- No personal information is required to use the service
- No tracking cookies or analytics

---

## Maintenance

### Monitoring
- Daily freshness check: are forecasts being generated?
- Weekly accuracy comparison: predicted vs actual rates
- Model health monitoring: are all models loaded and responding?

### Retraining Schedule
- **Daily**: Fast refit (uses existing parameters, updates with new data)
- **Weekly**: Full retrain (re-optimizes hyperparameters)
- **On-demand**: Manual retrain trigger available via API

### Version History
| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | June 2026 | Initial release with 5-model ensemble |