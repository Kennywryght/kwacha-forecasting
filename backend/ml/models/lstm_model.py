import os
import random
import logging
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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

# ---------------------------------------------------
# REPRODUCIBILITY
# ---------------------------------------------------
SEED = 42

np.random.seed(SEED)
tf.random.set_seed(SEED)
random.seed(SEED)


class LSTMForecaster:

    def __init__(self, sequence_length=10):

        self.sequence_length = sequence_length

        self.model = None

        self.x_scaler = MinMaxScaler()
        self.y_scaler = MinMaxScaler()

        self.metrics = {}

        self.model_path = "ml/artifacts/lstm_model.keras"

        self.feature_columns = []

        self.is_fitted = False

    # ---------------------------------------------------
    # CREATE SEQUENCES
    # ---------------------------------------------------
    def create_sequences(self, X, y):

        X_seq = []
        y_seq = []

        for i in range(self.sequence_length, len(X)):

            X_seq.append(
                X[i - self.sequence_length:i]
            )

            y_seq.append(y[i])

        return np.array(X_seq), np.array(y_seq)

    # ---------------------------------------------------
    # CLEAN DATA
    # ---------------------------------------------------
    def clean_dataframe(self, df):

        df = df.copy()

        if "rate" not in df.columns:
            raise ValueError(
                "Dataset must contain 'rate' column"
            )

        # Keep dates separately
        dates = None

        if "date" in df.columns:
            dates = pd.to_datetime(df["date"])

            df = df.drop(columns=["date"])

        # Numeric only
        df = df.select_dtypes(include=[np.number])

        # Replace infinities
        df = df.replace(
            [np.inf, -np.inf],
            np.nan
        )

        # Fill missing values
        df = df.ffill().bfill()

        # Drop remaining NaNs
        df = df.dropna()

        return df, dates

    # ---------------------------------------------------
    # FIT PREPROCESSING
    # ---------------------------------------------------
    def fit_preprocess(self, df):

        df, _ = self.clean_dataframe(df)

        self.feature_columns = [
            c for c in df.columns
            if c != "rate"
        ]

        X = df[self.feature_columns].values

        y = df["rate"].values.reshape(-1, 1)

        # Fit ONLY during training
        X_scaled = self.x_scaler.fit_transform(X)

        y_scaled = self.y_scaler.fit_transform(y)

        return X_scaled, y_scaled

    # ---------------------------------------------------
    # TRANSFORM ONLY
    # ---------------------------------------------------
    def transform_preprocess(self, df):

        df, dates = self.clean_dataframe(df)

        X = df[self.feature_columns].values

        y = df["rate"].values.reshape(-1, 1)

        # IMPORTANT:
        # NO FITTING HERE
        X_scaled = self.x_scaler.transform(X)

        y_scaled = self.y_scaler.transform(y)

        return X_scaled, y_scaled, dates

    # ---------------------------------------------------
    # BUILD MODEL
    # ---------------------------------------------------
    def build_model(self, input_shape):

        model = Sequential()

        model.add(
            LSTM(
                64,
                return_sequences=True,
                input_shape=input_shape
            )
        )

        model.add(Dropout(0.2))

        model.add(
            LSTM(32)
        )

        model.add(Dropout(0.2))

        model.add(Dense(16, activation="relu"))

        model.add(Dense(1))

        optimizer = Adam(
            learning_rate=0.001,
            clipnorm=1.0
        )

        model.compile(
            optimizer=optimizer,
            loss="mse"
        )

        return model

    # ---------------------------------------------------
    # TRAIN
    # ---------------------------------------------------
    def fit(self, train_df):

        logger.info(
            "🚀 Training LSTM model..."
        )

        X_scaled, y_scaled = self.fit_preprocess(
            train_df
        )

        X_seq, y_seq = self.create_sequences(
            X_scaled,
            y_scaled
        )

        if len(X_seq) == 0:
            raise ValueError(
                "Sequence creation failed. "
                "Dataset too small."
            )

        logger.info(
            f"LSTM training sequences: {X_seq.shape}"
        )

        self.model = self.build_model(
            (
                X_seq.shape[1],
                X_seq.shape[2]
            )
        )

        early_stop = EarlyStopping(
            monitor="val_loss",
            patience=5,
            restore_best_weights=True
        )

        self.model.fit(
            X_seq,
            y_seq,
            epochs=30,
            batch_size=16,
            validation_split=0.1,
            verbose=1,
            callbacks=[early_stop]
        )

        self.is_fitted = True

        logger.info(
            "✅ LSTM training complete"
        )

    # ---------------------------------------------------
    # PREDICT
    # ---------------------------------------------------
    def predict(self, test_df):

        if not self.is_fitted:
            raise ValueError(
                "Model not trained"
            )

        X_scaled, y_scaled, dates = (
            self.transform_preprocess(test_df)
        )

        X_seq, y_seq = self.create_sequences(
            X_scaled,
            y_scaled
        )

        predictions_scaled = self.model.predict(
            X_seq
        )

        predictions = (
            self.y_scaler.inverse_transform(
                predictions_scaled
            )
        )

        y_true = (
            self.y_scaler.inverse_transform(
                y_seq
            )
        )

        result = pd.DataFrame({

            "date":
            dates.iloc[self.sequence_length:].values,

            "y_true":
            y_true.flatten(),

            "y_pred":
            predictions.flatten()

        })

        return result

    # ---------------------------------------------------
    # EVALUATE
    # ---------------------------------------------------
    def evaluate(self, predictions):

        y_true = predictions["y_true"]

        y_pred = predictions["y_pred"]

        rmse = np.sqrt(
            mean_squared_error(
                y_true,
                y_pred
            )
        )

        mae = mean_absolute_error(
            y_true,
            y_pred
        )

        mape = np.mean(
            np.abs(
                (y_true - y_pred) / y_true
            )
        ) * 100

        r2 = r2_score(
            y_true,
            y_pred
        )

        self.metrics = {

            "rmse": float(rmse),

            "mae": float(mae),

            "mape": float(mape),

            "r_squared": float(r2)

        }

        logger.info(
            f"📊 LSTM Metrics: {self.metrics}"
        )

        return self.metrics

    # ---------------------------------------------------
    # SAVE RESULTS
    # ---------------------------------------------------
    def save_results(self, predictions):

        os.makedirs(
            "outputs/metrics",
            exist_ok=True
        )

        os.makedirs(
            "outputs/plots",
            exist_ok=True
        )

        predictions.to_csv(
            "outputs/metrics/lstm_predictions.csv",
            index=False
        )

        pd.DataFrame([self.metrics]).to_csv(
            "outputs/metrics/lstm_metrics.csv",
            index=False
        )

        plt.figure(figsize=(12, 6))

        plt.plot(
            predictions["date"],
            predictions["y_true"],
            label="Actual"
        )

        plt.plot(
            predictions["date"],
            predictions["y_pred"],
            label="Forecast"
        )

        plt.title(
            "LSTM Forecast vs Actual"
        )

        plt.xlabel("Date")

        plt.ylabel("Exchange Rate")

        plt.legend()

        plt.tight_layout()

        plt.savefig(
            "outputs/plots/lstm_forecast.png"
        )

        plt.close()

        logger.info(
            "📈 LSTM outputs saved"
        )

    # ---------------------------------------------------
    # SAVE MODEL
    # ---------------------------------------------------
    def save(self):

        os.makedirs(
            os.path.dirname(
                self.model_path
            ),
            exist_ok=True
        )

        self.model.save(
            self.model_path
        )

        joblib.dump(
            self.x_scaler,
            "ml/artifacts/lstm_x_scaler.pkl"
        )

        joblib.dump(
            self.y_scaler,
            "ml/artifacts/lstm_y_scaler.pkl"
        )

        joblib.dump(
            self.feature_columns,
            "ml/artifacts/lstm_features.pkl"
        )

        logger.info(
            "💾 LSTM model saved"
        )

    # ---------------------------------------------------
    # LOAD MODEL
    # ---------------------------------------------------
    def load(self):

        from tensorflow.keras.models import load_model

        self.model = load_model(
            self.model_path
        )

        self.x_scaler = joblib.load(
            "ml/artifacts/lstm_x_scaler.pkl"
        )

        self.y_scaler = joblib.load(
            "ml/artifacts/lstm_y_scaler.pkl"
        )

        self.feature_columns = joblib.load(
            "ml/artifacts/lstm_features.pkl"
        )

        self.is_fitted = True

        logger.info(
            "📂 LSTM model loaded"
        )