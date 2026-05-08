import numpy as np
import pandas as pd


class BaseForecaster:

    def __init__(self, name: str):
        self.name = name
        self.is_fitted = False
        self.metrics = {}

    def _business_dates(self, start, horizon: int):
        start = pd.to_datetime(start)
        return pd.bdate_range(start=start, periods=horizon).tolist()

    def _safe_metric(self, key, default=999):
        try:
            if not self.metrics:
                return default

            val = self.metrics.get(key, default)

            if val is None:
                return default

            if isinstance(val, (float, np.floating)):
                if np.isnan(val) or np.isinf(val):
                    return default

            return val

        except Exception:
            return default

    def _clean_dataframe(self, df):
        df = df.copy()

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        df = df.drop_duplicates()
        df = df.replace([np.inf, -np.inf], np.nan)

        if "date" in df.columns:
            df = df.sort_values("date")

        df = df.ffill().bfill()
        df = df.dropna()

        return df.reset_index(drop=True)

    def _forecast_output(self, dates, predicted, lower, upper):
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "predicted": list(map(float, predicted)),
            "lower_bound": list(map(float, lower)),
            "upper_bound": list(map(float, upper)),
        }

    def fit(self, df):
        raise NotImplementedError

    def predict(self, data):
        raise NotImplementedError

    def save(self, path):
        raise NotImplementedError

    def load(self, path):
        raise NotImplementedError