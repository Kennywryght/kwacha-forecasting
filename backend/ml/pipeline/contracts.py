# Defines strict data contracts for ML pipeline stages

RAW_COLUMNS = ["date", "rate"]

CLEANED_REQUIRED_COLUMNS = ["date", "rate"]

ENGINEERED_REQUIRED_COLUMNS = [
    "date", "rate",
    "daily_return"
]

MODEL_TYPES = ["arima", "arimax", "prophet", "lstm"]