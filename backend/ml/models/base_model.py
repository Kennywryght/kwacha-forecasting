import numpy as np
import pandas as pd


class BaseForecaster:
    def __init__(self, name: str):
        self.name = name
        self.is_fitted = False
        self.train_start = None
        self.train_end = None
        self.metrics = {}

    def _business_dates(self, start, horizon: int):
        """
        FIX:
        - ensure pandas datetime safety
        - avoid dtype errors in forecasting
        """
        start = pd.to_datetime(start)
        return pd.bdate_range(start=start, periods=horizon).tolist()