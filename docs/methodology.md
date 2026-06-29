# KwachaCast Methodology

## Overview
KwachaCast uses an ensemble of 5 forecasting models to predict MWK/USD exchange rates at 1-day, 7-day, and 30-day horizons. The system is trained on 13+ years of daily exchange rate data from the Reserve Bank of Malawi.

---

## Data Sources

| Source | Data | Frequency | Period |
|--------|------|-----------|--------|
| Reserve Bank of Malawi | MWK/USD exchange rate | Daily | 2013–present |
| Open Exchange Rates API | Live MWK/USD rate | Real-time | Current |
| National Statistical Office | Inflation, interest rates | Monthly | 2013–present |
| Federal Reserve (FRED) | US CPI, Fed funds rate | Monthly | 2013–present |

---

## Feature Engineering (42 Features)

Features are created from the raw exchange rate to help models learn temporal patterns.

### 1. Lag Features (7 features)
Past exchange rates at different time intervals.

| Feature | Description |
|---------|-------------|
| lag_1 | Yesterday's rate |
| lag_3 | Rate 3 days ago |
| lag_7 | Rate 1 week ago |
| lag_14 | Rate 2 weeks ago |
| lag_30 | Rate 1 month ago |
| lag_60 | Rate 2 months ago |
| lag_90 | Rate 3 months ago |

### 2. Rolling Statistics (10 features)
Moving averages and standard deviations over different windows.

| Feature | Window |
|---------|--------|
| rolling_mean_7, rolling_std_7 | 7 days |
| rolling_mean_14, rolling_std_14 | 14 days |
| rolling_mean_30, rolling_std_30 | 30 days |
| rolling_mean_60, rolling_std_60 | 60 days |
| rolling_mean_90, rolling_std_90 | 90 days |

### 3. Momentum & Rate of Change (8 features)
Measures of how fast the rate is moving.

| Feature | Formula |
|---------|---------|
| momentum_7 | rate_today - rate_7_days_ago |
| momentum_14 | rate_today - rate_14_days_ago |
| momentum_30 | rate_today - rate_30_days_ago |
| momentum_60 | rate_today - rate_60_days_ago |
| roc_7, roc_14, roc_30, roc_60 | Percentage change over period |

### 4. Temporal Features (7 features)
Calendar-based features to capture seasonal patterns.

- year, month, quarter
- day_of_week, day_of_year, week_of_year
- is_weekend (binary flag)

### 5. Cyclical Encodings (6 features)
Mathematical transformation of temporal features to preserve circular nature.

month_sin = sin(2π × month / 12)
month_cos = cos(2π × month / 12)
dow_sin = sin(2π × day_of_week / 7)
dow_cos = cos(2π × day_of_week / 7)
quarter_sin = sin(2π × quarter / 4)
quarter_cos = cos(2π × quarter / 4)


**Why?** Without cyclical encoding, December (12) and January (1) appear far apart (|12-1|=11). With sine/cosine, they are correctly represented as adjacent months.

### 6. Macroeconomic Differentials (3 features)
Economic theory-based features.

| Feature | Formula | Theory |
|---------|---------|--------|
| inflation_diff | Malawi CPI - US CPI | Purchasing Power Parity |
| interest_rate_diff | Malawi lending rate - US Fed rate | Interest Rate Parity |
| real_interest_diff | Malawi real rate - US real rate | Real interest differential |

---

## Train/Test Split

Total data: 4,700+ daily observations (2013–2026)
Training: 85% (~4,000 records, 2013–2024)
Testing: 15% (~700 records, 2024–2026)


**Time-based split** (not random) to prevent data leakage. In production, you always predict the future from the past.

---

## Models

### ARIMA (AutoRegressive Integrated Moving Average)
- **Type**: Statistical time series model
- **Parameters**: Auto-selected using AIC (Akaike Information Criterion)
- **Grid search**: p ∈ [0,3], q ∈ [0,3] with d determined by ADF test
- **Strengths**: Well-understood, statistically rigorous
- **Limitations**: Assumes linear relationships, struggles with structural breaks

### ARIMAX (ARIMA with Exogenous Variables)
- **Type**: Statistical model with external regressors
- **Exogenous variables**: momentum_7, momentum_30, rolling_mean_7, inflation_diff, interest_rate_diff
- **Strengths**: Incorporates economic theory
- **Limitations**: Requires future values of exogenous variables (assumes current conditions persist)

### Prophet (Facebook)
- **Type**: Decomposition-based (trend + seasonality + holidays)
- **Key parameters**: changepoint_prior_scale=0.05, n_changepoints=25
- **Strengths**: Handles structural breaks, robust to outliers
- **Limitations**: Designed for business forecasting, not specifically for exchange rates

### XGBoost (Extreme Gradient Boosting)
- **Type**: Gradient boosting machine learning
- **Hyperparameter tuning**: RandomizedSearchCV, 20 iterations, 3-fold CV
- **Parameters tuned**: n_estimators, max_depth, learning_rate, subsample, colsample_bytree
- **Strengths**: Captures non-linear patterns, feature importance
- **Limitations**: Requires feature engineering, doesn't model time dependency explicitly

### LightGBM (Light Gradient Boosting Machine)
- **Type**: Gradient boosting with leaf-wise growth
- **Hyperparameter tuning**: RandomizedSearchCV, 20 iterations, 3-fold CV
- **Parameters tuned**: n_estimators, max_depth, learning_rate, num_leaves, subsample
- **Strengths**: Faster training than XGBoost, handles large feature sets
- **Limitations**: Can overfit on small datasets

### Ensemble
- **Type**: Weighted average of all models
- **Weighting scheme**: Inverse RMSE (lower error = higher weight)
- **Minimum weight**: 5% per model
- **Fallback**: Equal weights if metrics unavailable
- **Strengths**: More robust than any single model, errors cancel out
- **Limitations**: Requires all component models to be fitted

---

## Evaluation Metrics

### MAPE (Mean Absolute Percentage Error)

MAPE = (100/n) × Σ|actual - predicted| / actual

- **Interpretation**: Average percentage error
- **Our result**: 0.30% (exceptional for currency forecasting)
- **Industry standard**: 1-5% for exchange rate forecasting

### RMSE (Root Mean Square Error)


RMSE = √(Σ(actual - predicted)² / n)

- **Interpretation**: Typical error magnitude in MWK
- **Our result**: 4.88 MWK
- **Characteristic**: Penalizes large errors more than small ones

### R² (Coefficient of Determination)

R² = 1 - (SS_residual / SS_total)

- **Interpretation**: Proportion of variance explained
- **Our result**: 0.991 (99.1% of rate variation explained)

### Directional Accuracy

Directional Accuracy = correct_direction_predictions / total_predictions

- **Interpretation**: How often we correctly predict up vs down
- **Our result**: 78%
- **Value**: Even if magnitude is slightly off, knowing direction is actionable

---

## Why 0.30% MAPE is Achievable

Malawi operates a managed exchange rate regime. Unlike free-floating currencies (which can swing 2-5% daily), the MWK/USD rate typically moves less than 0.5% per day. This stability makes short-term forecasting more accurate than it would be for volatile currency pairs.

However, this also means the models are tuned to a managed regime. Structural changes (such as devaluations) may temporarily reduce accuracy until the models adapt.

---

## Model Selection Rationale

We use 5 different models because:

1. **Different assumptions**: ARIMA assumes linearity, Prophet decomposes trends, XGBoost captures non-linear patterns
2. **Error diversity**: Models make different types of mistakes — when averaged, errors cancel out
3. **Robustness**: If one model performs poorly, others compensate
4. **Empirical evidence**: Our ensemble consistently outperforms any single model