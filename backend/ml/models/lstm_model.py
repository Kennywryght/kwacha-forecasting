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
from backend.ml.pipeline.feature_engineer import engineer_features 
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
        
        df = df.copy()
        
        # using the pipeline's powerful feature engineer
        df, _ = engineer_features(df)
        
        #drop non-numeric columns
        exclude_cols = ['date', 'rate']
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        self.feature_columns = feature_cols
        
        x = df[feature_cols].values
        y = df["rate"].values.reshape(-1, 1)
        
        return x, y, df # return df too 

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

        model = Sequential([
            LSTM(64, input_shape=input_shape, return_sequences=True),
            Dropout(0.25),
            LSTM(32, return_sequences=False),
            Dropout(0.5),
            Dense(16, activation="relu"),
            Dense(1)
        ])

        model.compile(
            optimizer=Adam(learning_rate=0.0008),
            loss=tf.keras.losses.Huber(delta=1.0)
        )

        return model

    # =====================================================
    # TRAIN
    # =====================================================

    def fit(self, train_df):

        logger.info("🚀 Training LSTM model...")

        X, y, _ = self.prepare_features(train_df)

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

        X, y, df_test = self.prepare_features(test_df)

        X_scaled = self.x_scaler.transform(X)
        
        X_seq, _ = self.create_sequences(
            X_scaled,
            np.zeros_like(y) # dummy y for sequence creation
        )
        
        predictions_scaled = self.model.predict(X_seq, verbose=0)
        
        predictions = self.y_scaler.inverse_transform(predictions_scaled.reshape(-1, 1))
        
        # align y_true with the actual sequences used 
        y_true = y[self.sequence_length:].reshape(-1, 1)
        
        return {
            "y_true": y_true.flatten(),
            "y_pred": predictions.flatten(),
            "dates": df_test["date"].iloc[self.sequence_length:] .values
        }
        
    print(f"Prediction range: {predictions.min():.4f} — {predictions.max():.4f}")
    print(f"Actual range: {y_true.min():.4f} — {y_true.max():.4f}") 
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