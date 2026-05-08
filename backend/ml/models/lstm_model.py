import os
import logging
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

logger = logging.getLogger(__name__)


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

    # -----------------------------
    # CREATE SEQUENCES
    # -----------------------------
    def create_sequences(self, X, y):
        X_seq = []
        y_seq = []

        for i in range(self.sequence_length, len(X)):
            X_seq.append(X[i - self.sequence_length:i])
            y_seq.append(y[i])

        return np.array(X_seq), np.array(y_seq)

    # -----------------------------
    # PREPROCESS DATA
    # -----------------------------
    def preprocess(self, df):
        if "rate" not in df.columns:
            raise ValueError("Dataset must contain 'rate' column")

        df = df.copy()

        # Drop date column if exists
        if "date" in df.columns:
            df = df.drop(columns=["date"])

        # Keep numeric only
        df = df.select_dtypes(include=[np.number])

        # Replace inf values
     
        df = df.replace([np.inf, -np.inf], np.nan)

        # Fill missing values
        df = df.ffill().bfill()

        # Final safety
        df = df.dropna()

        self.feature_columns = [c for c in df.columns if c != "rate"]

        X = df[self.feature_columns].values
        y = df["rate"].values.reshape(-1, 1)

        # Separate scalers
        self.x_scaler = MinMaxScaler()
        self.y_scaler = MinMaxScaler()

        X_scaled = self.x_scaler.fit_transform(X)
        y_scaled = self.y_scaler.fit_transform(y)

        return X_scaled, y_scaled

    # -----------------------------
    # BUILD MODEL
    # -----------------------------
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

        model.add(LSTM(32))

        model.add(Dropout(0.2))

        model.add(Dense(1))

        model.compile(
            optimizer="adam",
            loss="mse"
        )

        return model

    # -----------------------------
    # TRAIN MODEL
    # -----------------------------
    def fit(self, train_df):
        logger.info("🚀 Training LSTM model...")

        X_scaled, y_scaled = self.preprocess(train_df)

        X_seq, y_seq = self.create_sequences(X_scaled, y_scaled)

        self.model = self.build_model(
            (X_seq.shape[1], X_seq.shape[2])
        )

        early_stop = EarlyStopping(
            monitor="loss",
            patience=5,
            restore_best_weights=True
        )

        self.model.fit(
            X_seq,
            y_seq,
            epochs=30,
            batch_size=16,
            verbose=1,
            callbacks=[early_stop]
        )

        self.is_fitted = True

        logger.info("✅ LSTM training complete")

    # -----------------------------
    # PREDICT
    # -----------------------------
    def predict(self, test_df):
        if not self.is_fitted:
            raise ValueError("Model not trained")

        X_scaled, y_scaled = self.preprocess(test_df)

        X_seq, y_seq = self.create_sequences(X_scaled, y_scaled)

        predictions_scaled = self.model.predict(X_seq)

        predictions = self.y_scaler.inverse_transform(predictions_scaled)
        y_true = self.y_scaler.inverse_transform(y_seq)

        result = pd.DataFrame({
            "y_true": y_true.flatten(),
            "y_pred": predictions.flatten()
        })

        return result

    # -----------------------------
    # EVALUATE
    # -----------------------------
    def evaluate(self, predictions):
        y_true = predictions["y_true"]
        y_pred = predictions["y_pred"]

        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)

        mape = np.mean(
            np.abs((y_true - y_pred) / y_true)
        ) * 100

        self.metrics = {
            "rmse": rmse,
            "mae": mae,
            "mape": mape,
        }

        logger.info(f"📊 LSTM Metrics: {self.metrics}")

        return self.metrics

    # -----------------------------
    # SAVE RESULTS
    # -----------------------------
    def save_results(self, predictions):
        os.makedirs("outputs/metrics", exist_ok=True)
        os.makedirs("outputs/plots", exist_ok=True)

        # Save predictions
        predictions.to_csv(
            "outputs/metrics/lstm_predictions.csv",
            index=False
        )

        # Save metrics
        pd.DataFrame([self.metrics]).to_csv(
            "outputs/metrics/lstm_metrics.csv",
            index=False
        )

        # Plot
        plt.figure(figsize=(10, 5))

        plt.plot(
            predictions["y_true"].values,
            label="Actual"
        )

        plt.plot(
            predictions["y_pred"].values,
            label="Forecast"
        )

        plt.title("LSTM Forecast vs Actual")
        plt.xlabel("Time")
        plt.ylabel("Exchange Rate")

        plt.legend()

        plt.savefig("outputs/plots/lstm_forecast.png")

        plt.close()

        logger.info("📈 LSTM outputs saved")

    # -----------------------------
    # SAVE MODEL
    # -----------------------------
    def save(self):
        os.makedirs(
            os.path.dirname(self.model_path),
            exist_ok=True
        )

        self.model.save(self.model_path)

        joblib.dump(
            self.y_scaler,
            "ml/artifacts/lstm_y_scaler.pkl"
        )

        logger.info("💾 LSTM model saved")

    # -----------------------------
    # LOAD MODEL
    # -----------------------------
    def load(self):
        from tensorflow.keras.models import load_model

        self.model = load_model(self.model_path)

        self.y_scaler = joblib.load(
            "ml/artifacts/lstm_y_scaler.pkl"
        )

        self.is_fitted = True

        logger.info("📂 LSTM model loaded")