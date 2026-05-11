# backend/ml/models/lstm_model.py

import os
import random
import logging
import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score
)

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.optimizers import Adam

logger = logging.getLogger(__name__)

SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)
random.seed(SEED)


class LSTMForecaster:

    def __init__(self, sequence_length=30):

        self.sequence_length = sequence_length

        self.model = None

        self.x_scaler = MinMaxScaler()
        self.y_scaler = MinMaxScaler()

        self.feature_columns = []

        self.metrics = {}

        self.is_fitted = False

    # =====================================================
    # CLEAN DATA
    # =====================================================

    def clean_dataframe(self, df):

        df = df.copy()

        if "rate" not in df.columns:
            raise ValueError("Dataset must contain 'rate' column")

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")

        df = df.replace([np.inf, -np.inf], np.nan)

        df = df.ffill().bfill()

        df = df.dropna()

        return df

    # =====================================================
    # FEATURE ENGINEERING
    # =====================================================

    def prepare_features(self, df):

        df = self.clean_dataframe(df)

        df["lag_1"] = df["rate"].shift(1)
        df["lag_2"] = df["rate"].shift(2)
        df["lag_3"] = df["rate"].shift(3)

        df = df.dropna()

        self.feature_columns = ["lag_1", "lag_2", "lag_3"]

        X = df[self.feature_columns].values

        y = df["rate"].values.reshape(-1, 1)

        return X, y

    # =====================================================
    # CREATE SEQUENCES
    # =====================================================

    def create_sequences(self, X, y):

        X_seq = []
        y_seq = []

        for i in range(self.sequence_length, len(X)):

            X_seq.append(
                X[i - self.sequence_length:i]
            )

            y_seq.append(y[i])

        return np.array(X_seq), np.array(y_seq)

    # =====================================================
    # BUILD MODEL
    # =====================================================

    def build_model(self, input_shape):

        model = Sequential()

        model.add(
            LSTM(
                32,
                input_shape=input_shape,
                return_sequences=False
            )
        )

        model.add(Dropout(0.2))

        model.add(Dense(16, activation="relu"))

        model.add(Dense(1))

        optimizer = Adam(
            learning_rate=0.001
        )

        model.compile(
            optimizer=optimizer,
            loss="mse"
        )

        return model

    # =====================================================
    # TRAIN
    # =====================================================

    def fit(self, train_df):

        logger.info("🚀 Training LSTM model...")

        X, y = self.prepare_features(train_df)

        X_scaled = self.x_scaler.fit_transform(X)

        y_scaled = self.y_scaler.fit_transform(y)

        X_seq, y_seq = self.create_sequences(
            X_scaled,
            y_scaled
        )

        if len(X_seq) == 0:
            raise ValueError("Dataset too small")

        self.model = self.build_model(
            (X_seq.shape[1], X_seq.shape[2])
        )

        early_stop = EarlyStopping(
            monitor="val_loss",
            patience=5,
            restore_best_weights=True
        )

        self.model.fit(
            X_seq,
            y_seq,
            epochs=20,
            batch_size=16,
            validation_split=0.2,
            callbacks=[early_stop],
            verbose=1
        )

        self.is_fitted = True

        logger.info("✅ LSTM training complete")

    # =====================================================
    # PREDICT
    # =====================================================

    def predict(self, test_df):

        if not self.is_fitted:
            raise RuntimeError("Model not fitted")

        X, y = self.prepare_features(test_df)

        X_scaled = self.x_scaler.transform(X)

        y_scaled = self.y_scaler.transform(y)

        X_seq, y_seq = self.create_sequences(
            X_scaled,
            y_scaled
        )

        predictions_scaled = self.model.predict(X_seq)

        # IMPORTANT FIX
        predictions = self.y_scaler.inverse_transform(
            predictions_scaled.reshape(-1, 1)
        )

        y_true = self.y_scaler.inverse_transform(
            y_seq.reshape(-1, 1)
        )

        return {
            "y_true": y_true.flatten(),
            "y_pred": predictions.flatten()
        }

    # =====================================================
    # EVALUATE
    # =====================================================

    def evaluate(self, predictions):

        y_true = predictions["y_true"]

        y_pred = predictions["y_pred"]

        self.metrics = {

            "rmse": float(
                np.sqrt(
                    mean_squared_error(y_true, y_pred)
                )
            ),

            "mae": float(
                mean_absolute_error(y_true, y_pred)
            ),

            "mape": float(
                np.mean(
                    np.abs(
                        (y_true - y_pred) / y_true
                    )
                ) * 100
            ),

            "r_squared": float(
                r2_score(y_true, y_pred)
            )
        }

        logger.info(f"📊 LSTM Metrics: {self.metrics}")

        return self.metrics