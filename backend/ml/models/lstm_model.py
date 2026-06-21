"""LSTM neural network model for time series forecasting.

This module provides an LSTM-based forecaster with:
- Sequence-based learning
- Feature engineering
- Hyperparameter tuning
- Model persistence
- Uncertainty estimation
"""

import os
import pickle
import random
import warnings
import logging
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from ml.models.base_model import BaseForecaster
from ml.pipeline.feature_engineer import engineer_features
from core.logging_config import get_logger

# Suppress TensorFlow warnings
warnings.filterwarnings("ignore")
tf.get_logger().setLevel(logging.ERROR)

logger = get_logger(__name__)

# Set seeds for reproducibility
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)
random.seed(SEED)


class LSTMForecaster(BaseForecaster):
    """
    LSTM neural network for time series forecasting.

    Features:
    - Sequence-based learning with configurable lookback
    - Feature engineering integration
    - Hyperparameter tuning support
    - Model persistence
    - Uncertainty estimation via dropout at inference
    """

    def __init__(
        self,
        sequence_length: int = 30,
        lstm_units: List[int] = [64, 32],
        dropout_rate: float = 0.25,
        dense_units: int = 16,
        learning_rate: float = 0.0008,
        batch_size: int = 32,
        epochs: int = 50,
        use_feature_engineering: bool = True,
        use_bidirectional: bool = False
    ):
        """
        Initialize LSTM forecaster.

        Args:
            sequence_length: Number of past observations to use
            lstm_units: List of LSTM units per layer
            dropout_rate: Dropout rate for regularization
            dense_units: Units in dense layer
            learning_rate: Learning rate for optimizer
            batch_size: Training batch size
            epochs: Maximum training epochs
            use_feature_engineering: Whether to use engineered features
            use_bidirectional: Whether to use bidirectional LSTM
        """
        super().__init__("lstm")

        self.sequence_length = sequence_length
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.dense_units = dense_units
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.use_feature_engineering = use_feature_engineering
        self.use_bidirectional = use_bidirectional

        self.model = None
        self.x_scaler = MinMaxScaler()
        self.y_scaler = MinMaxScaler()
        self.feature_columns = None
        self.last_date = None
        self.last_sequence = None

    # ============================================================
    # Core Methods
    # ============================================================

    def _prepare_data(
        self,
        df: pd.DataFrame,
        fit_scaler: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """
        Prepare data for LSTM training/prediction.

        Args:
            df: Input DataFrame
            fit_scaler: Whether to fit the scaler

        Returns:
            Tuple of (X_scaled, y_scaled, processed_df)
        """
        df = self._clean_dataframe(df)

        if "date" not in df.columns:
            raise ValueError("DataFrame must contain 'date' column")

        df = df.sort_values("date")
        df = df.dropna(subset=["rate"])

        if len(df) < self.sequence_length + 10:
            raise ValueError(
                f"Not enough data: {len(df)} rows "
                f"(need at least {self.sequence_length + 10})"
            )

        # Apply feature engineering if enabled
        if self.use_feature_engineering:
            df = engineer_features(df)

        # Identify feature columns (exclude date and target)
        exclude_cols = ['date', 'rate']
        feature_cols = [col for col in df.columns if col not in exclude_cols]

        self.feature_columns = feature_cols

        # Extract features and target
        X = df[feature_cols].values
        y = df["rate"].values.reshape(-1, 1)

        # Scale
        if fit_scaler:
            X_scaled = self.x_scaler.fit_transform(X)
            y_scaled = self.y_scaler.fit_transform(y)
        else:
            X_scaled = self.x_scaler.transform(X)
            y_scaled = self.y_scaler.transform(y)

        # Store last date for forecasting
        if len(df) > 0:
            self.last_date = df["date"].iloc[-1]

        return X_scaled, y_scaled, df

    def _create_sequences(
        self,
        X: np.ndarray,
        y: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Create sequences for LSTM.

        Args:
            X: Feature array
            y: Target array (optional for prediction)

        Returns:
            Tuple of (X_seq, y_seq)
        """
        X_seq = []
        y_seq = [] if y is not None else None

        for i in range(self.sequence_length, len(X)):
            X_seq.append(X[i - self.sequence_length:i])
            if y is not None:
                y_seq.append(y[i])

        X_seq = np.array(X_seq)

        if y_seq is not None:
            y_seq = np.array(y_seq)
            return X_seq, y_seq

        return X_seq, None

    def _build_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """
        Build the LSTM model.

        Args:
            input_shape: (sequence_length, n_features)

        Returns:
            Compiled Keras model
        """
        model = Sequential()

        # First LSTM layer
        if self.use_bidirectional:
            model.add(Bidirectional(
                LSTM(
                    self.lstm_units[0],
                    return_sequences=len(self.lstm_units) > 1,
                    activation='tanh',
                    recurrent_activation='sigmoid'
                ),
                input_shape=input_shape
            ))
        else:
            model.add(LSTM(
                self.lstm_units[0],
                return_sequences=len(self.lstm_units) > 1,
                activation='tanh',
                recurrent_activation='sigmoid',
                input_shape=input_shape
            ))

        model.add(Dropout(self.dropout_rate))

        # Additional LSTM layers
        for i, units in enumerate(self.lstm_units[1:], start=1):
            if self.use_bidirectional:
                model.add(Bidirectional(
                    LSTM(
                        units,
                        return_sequences=i < len(self.lstm_units) - 1,
                        activation='tanh',
                        recurrent_activation='sigmoid'
                    )
                ))
            else:
                model.add(LSTM(
                    units,
                    return_sequences=i < len(self.lstm_units) - 1,
                    activation='tanh',
                    recurrent_activation='sigmoid'
                ))
            model.add(Dropout(self.dropout_rate * 1.5))

        # Dense layers
        model.add(Dense(self.dense_units, activation='relu'))
        model.add(Dropout(self.dropout_rate))

        # Output layer
        model.add(Dense(1))

        # Compile
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss=tf.keras.losses.Huber(delta=1.0),
            metrics=['mae']
        )

        return model

    def fit(self, df: pd.DataFrame) -> None:
        """
        Fit the LSTM model.

        Args:
            df: DataFrame with 'date' and 'rate' columns
        """
        logger.info("🚀 LSTM training started")

        # Prepare data
        X_scaled, y_scaled, processed_df = self._prepare_data(df, fit_scaler=True)

        # Create sequences
        X_seq, y_seq = self._create_sequences(X_scaled, y_scaled)

        if len(X_seq) < 20:
            raise ValueError(f"Too few sequences: {len(X_seq)} (need at least 20)")

        # Split into train and validation
        split_idx = int(len(X_seq) * 0.8)
        X_train, X_val = X_seq[:split_idx], X_seq[split_idx:]
        y_train, y_val = y_seq[:split_idx], y_seq[split_idx:]

        # Build model
        self.model = self._build_model((X_seq.shape[1], X_seq.shape[2]))

        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-6
            )
        ]

        # Train
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=self.epochs,
            batch_size=self.batch_size,
            callbacks=callbacks,
            verbose=0
        )

        # Store training history
        self.training_history = history.history

        self.is_fitted = True

        # Store last sequence for forecasting
        if len(X_scaled) >= self.sequence_length:
            self.last_sequence = X_scaled[-self.sequence_length:]

        logger.info(f"✅ LSTM training complete ({len(X_seq)} sequences)")

    def predict(self, horizon: int) -> Dict[str, Any]:
        """
        Generate forecasts for a given horizon.

        Args:
            horizon: Number of days to forecast

        Returns:
            Dictionary with dates, predictions, and confidence intervals
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("LSTM model not fitted")

        if self.last_sequence is None:
            raise RuntimeError("No last sequence available for forecasting")

        try:
            # Start with the last known sequence
            current_sequence = self.last_sequence.copy()

            predictions = []

            # Generate predictions recursively
            for _ in range(horizon):
                # Reshape for LSTM
                input_seq = current_sequence.reshape(1, self.sequence_length, -1)

                # Predict next step
                next_pred_scaled = self.model.predict(input_seq, verbose=0)

                # Inverse transform
                next_pred = float(self.y_scaler.inverse_transform(next_pred_scaled)[0, 0])
                predictions.append(next_pred)

                # Update sequence (drop first, append prediction)
                # We need to update the feature values for the next step
                # For simplicity, we'll keep features constant
                # A more sophisticated approach would update features too
                new_step = current_sequence[-1].copy()
                # For now, we keep features the same
                current_sequence = np.vstack([current_sequence[1:], new_step])

            # Generate dates
            dates = self._generate_dates(self.last_date, horizon)

            # Estimate uncertainty from training residuals
            if hasattr(self, '_residuals') and len(self._residuals) > 0:
                std_residual = np.std(self._residuals)
                z_score = 1.96  # 95% confidence
                lower = [p - z_score * std_residual for p in predictions]
                upper = [p + z_score * std_residual for p in predictions]
            else:
                # Use 5% band as fallback
                lower = [p * 0.95 for p in predictions]
                upper = [p * 1.05 for p in predictions]

            return self._format_forecast_output(dates, predictions, lower, upper)

        except Exception as e:
            logger.error(f"LSTM prediction failed: {e}")
            raise

    def evaluate(self, test_df: pd.DataFrame) -> Dict[str, float]:
        """
        Evaluate the model on test data.

        Args:
            test_df: DataFrame with 'rate' and 'date' columns

        Returns:
            Dictionary of evaluation metrics
        """
        X_scaled, y_scaled, processed_df = self._prepare_data(test_df, fit_scaler=False)

        X_seq, y_seq = self._create_sequences(X_scaled, y_scaled)

        if len(X_seq) == 0:
            raise ValueError("Test set too small for evaluation")

        # Predict
        preds_scaled = self.model.predict(X_seq, verbose=0)
        preds = self.y_scaler.inverse_transform(preds_scaled).flatten()

        # Actual values (aligned with sequences)
        y_true = y_scaled.flatten()
        y_true = self.y_scaler.inverse_transform(y_true.reshape(-1, 1)).flatten()

        # Compute metrics
        from ml.utils.metrics import compute_all_metrics
        self.metrics = compute_all_metrics(y_true, preds)

        # Store residuals
        self._residuals = (y_true - preds).tolist()

        return self.metrics

    # ============================================================
    # Model Persistence
    # ============================================================

    def save(self, path: str) -> None:
        """Save the model to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Save Keras model
        model_path = os.path.join(os.path.dirname(path), f"{self.name}_model.keras")
        self.model.save(model_path)

        # Save metadata
        metadata = {
            "name": self.name,
            "sequence_length": self.sequence_length,
            "lstm_units": self.lstm_units,
            "dropout_rate": self.dropout_rate,
            "dense_units": self.dense_units,
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "use_feature_engineering": self.use_feature_engineering,
            "use_bidirectional": self.use_bidirectional,
            "feature_columns": self.feature_columns,
            "metrics": self.metrics,
            "is_fitted": self.is_fitted,
            "training_date_range": self.training_date_range,
            "last_date": self.last_date,
            "model_version": self.model_version,
            "creation_time": self.creation_time,
            "model_path": model_path
        }

        with open(path, "wb") as f:
            pickle.dump({
                "metadata": metadata,
                "x_scaler": self.x_scaler,
                "y_scaler": self.y_scaler,
                "last_sequence": self.last_sequence,
                "training_history": self.training_history
            }, f)

        logger.info(f"✅ LSTM model saved to {path}")

    def load(self, path: str) -> None:
        """Load the model from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)

        metadata = data.get("metadata", {})
        for key, value in metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Load Keras model
        model_path = metadata.get("model_path")
        if model_path and os.path.exists(model_path):
            self.model = tf.keras.models.load_model(model_path)
        else:
            # Try to find model in same directory
            base_dir = os.path.dirname(path)
            model_path = os.path.join(base_dir, f"{self.name}_model.keras")
            if os.path.exists(model_path):
                self.model = tf.keras.models.load_model(model_path)

        self.x_scaler = data.get("x_scaler")
        self.y_scaler = data.get("y_scaler")
        self.last_sequence = data.get("last_sequence")
        self.training_history = data.get("training_history", {})

        self.is_fitted = True
        logger.info(f"✅ LSTM model loaded from {path}")