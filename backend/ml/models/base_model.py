import numpy as np
import pandas as pd


class BaseForecaster:

    def __init__(self, name: str):

        self.name = name

        self.is_fitted = False

        self.metrics = {}

        self.train_start = None
        self.train_end = None

    # =====================================================
    # SAFE BUSINESS DATES
    # =====================================================
    def _business_dates(self, start, horizon: int):

        start = pd.to_datetime(start)

        return pd.bdate_range(
            start=start,
            periods=horizon
        ).tolist()

    # =====================================================
    # SAFE METRIC ACCESS
    # =====================================================
    def _safe_metric(self, key, default=999):

        try:

            if self.metrics is None:
                return default

            value = self.metrics.get(key, default)

            if value is None:
                return default

            if isinstance(value, float):

                if np.isnan(value):
                    return default

                if np.isinf(value):
                    return default

            return value

        except Exception:
            return default

    # =====================================================
    # COMMON DATA CLEANING
    # =====================================================
    def _clean_dataframe(self, df):

        df = df.copy()

        # safe datetime
        if "date" in df.columns:
            df["date"] = pd.to_datetime(
                df["date"],
                errors="coerce"
            )

        # remove duplicates
        df = df.drop_duplicates()

        # replace infinities
        df = df.replace(
            [np.inf, -np.inf],
            np.nan
        )

        # sort by date
        if "date" in df.columns:
            df = df.sort_values("date")

        # fill missing
        df = df.ffill().bfill()

        # final dropna
        df = df.dropna()

        return df.reset_index(drop=True)

    # =====================================================
    # TARGET VALIDATION
    # =====================================================
    def _validate_target(self, df):

        possible_targets = [
            "rate",
            "usd_mwk",
            "exchange_rate"
        ]

        for col in possible_targets:

            if col in df.columns:
                return col

        raise ValueError(
            "No valid target column found"
        )

    # =====================================================
    # SAFE CLIPPING
    # =====================================================
    def _clip_outliers(
        self,
        series,
        lower_q=0.01,
        upper_q=0.99
    ):

        lower = series.quantile(lower_q)
        upper = series.quantile(upper_q)

        return series.clip(
            lower=lower,
            upper=upper
        )

    # =====================================================
    # SAFE FEATURE EXTRACTION
    # =====================================================
    def _numeric_features(self, df, exclude=None):

        if exclude is None:
            exclude = []

        numeric_df = df.select_dtypes(
            include=[np.number]
        )

        cols = [
            c for c in numeric_df.columns
            if c not in exclude
        ]

        return numeric_df[cols]

    # =====================================================
    # FORECAST OUTPUT FORMAT
    # =====================================================
    def _forecast_output(
        self,
        dates,
        predicted,
        lower,
        upper
    ):

        return {
            "dates": [
                d.strftime("%Y-%m-%d")
                for d in dates
            ],
            "predicted": list(map(float, predicted)),
            "lower_bound": list(map(float, lower)),
            "upper_bound": list(map(float, upper))
        }

    # =====================================================
    # REQUIRED METHODS
    # =====================================================
    def fit(self, df):
        raise NotImplementedError

    def predict(self, horizon):
        raise NotImplementedError

    def save(self, path):
        raise NotImplementedError

    def load(self, path):
        raise NotImplementedError