"""
EDA Module for MWK/USD Exchange Rate Analysis
===============================================
Comprehensive exploratory data analysis with time-series diagnostics,
feature engineering insights, and automated reporting.
"""

import os
import warnings
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import TimeSeriesSplit
from sklearn.feature_selection import mutual_info_regression
from sklearn.decomposition import PCA
from sklearn.metrics import mean_squared_error, mean_absolute_error
from scipy import stats
from statsmodels.tsa.stattools import adfuller, grangercausalitytests
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.api import qqplot
import logging

# Optional dependencies
try:
    import ruptures as rpt
    RUPTURES_AVAILABLE = True
except ImportError:
    RUPTURES_AVAILABLE = False

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

try:
    import lightgbm as lgb
    LGB_AVAILABLE = True
except ImportError:
    LGB_AVAILABLE = False

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_PATH = "data/processed/mwk_usd_clean.csv"
PLOT_DIR = "outputs/plots"
REPORT_DIR = "outputs/reports"
os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ── Style Configuration ──────────────────────────────────────────────────────
PALETTE = {
    "rate": "#1A6BAF",
    "mean7": "#E05C2A",
    "mean30": "#2EAF6F",
    "std7": "#F5A623",
    "std30": "#9B59B6",
    "band": "#1A6BAF",
    "grid": "#E8EDF2",
    "bg": "#F7F9FC",
    "spine": "#CBD5E1",
    "positive": "#2EAF6F",
    "negative": "#E05C2A",
}
FONT_TITLE = dict(fontsize=16, fontweight="bold", color="#1A2535")
FONT_LABEL = dict(fontsize=11, color="#374151")
FONT_TICK = dict(labelsize=9, labelcolor="#6B7280")
FIG_DPI = 180

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.facecolor": PALETTE["bg"],
    "figure.facecolor": "white",
    "axes.grid": True,
    "grid.color": PALETTE["grid"],
    "grid.linewidth": 0.7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": True,
    "axes.spines.bottom": True,
})


# ══════════════════════════════════════════════════════════════════════════════
# 1. DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_data(path: str = DATA_PATH) -> pd.DataFrame:
    """Load and validate the dataset."""
    df = pd.read_csv(path, parse_dates=["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    print(f"\n{'═'*60}")
    print("  MWK/USD EDA — Key Insights")
    print(f"{'═'*60}")
    print(f"  Dataset  : {path}")
    print(f"  Rows     : {len(df):,}")
    print(f"  Columns  : {df.shape[1]}")
    print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  Rate range: {df['rate'].min():,.2f} – {df['rate'].max():,.2f} MWK/USD")

    total_depr = (df['rate'].iloc[-1] / df['rate'].iloc[0] - 1) * 100
    print(f"  Total depreciation: {total_depr:+.1f}%")

    missing = df.isnull().sum()
    if missing.any():
        print(f"  Missing values in: {missing[missing > 0].to_dict()}")
    else:
        print("  Missing values : None")

    print(f"{'═'*60}\n")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 2. ORIGINAL EDA PLOTS (Backward Compatible)
# ══════════════════════════════════════════════════════════════════════════════

def plot_time_series(df: pd.DataFrame) -> None:
    """Plot the main time series with annotations."""
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor("white")

    ax.fill_between(df["date"], df["rate"], alpha=0.12, color=PALETTE["band"])
    ax.plot(df["date"], df["rate"], color=PALETTE["rate"],
            linewidth=1.4, label="MWK/USD Rate")

    # Annotate min and max
    idx_min = df["rate"].idxmin()
    idx_max = df["rate"].idxmax()

    for idx, va, label in [(idx_min, "top", "Min"), (idx_max, "bottom", "Max")]:
        ax.annotate(
            f"{label}\n{df.loc[idx,'rate']:,.0f}",
            xy=(df.loc[idx, "date"], df.loc[idx, "rate"]),
            xytext=(30 if va == "top" else -40, 20 if va == "bottom" else -30),
            textcoords="offset points",
            fontsize=8.5,
            color="#374151",
            arrowprops=dict(arrowstyle="->", color="#9CA3AF", lw=0.9),
        )

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.tick_params(**FONT_TICK)
    ax.set_title("MWK / USD Exchange Rate (2013–2026)", **FONT_TITLE, pad=14)
    ax.set_xlabel("Date", **FONT_LABEL)
    ax.set_ylabel("MWK per 1 USD", **FONT_LABEL)
    ax.legend(fontsize=10, framealpha=0.7)

    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color(PALETTE["spine"])

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "time_series.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


def plot_rolling_stats(df: pd.DataFrame) -> None:
    """Plot rolling statistics with confidence bands."""
    windows = [7, 30]
    colors_mean = [PALETTE["mean7"], PALETTE["mean30"]]
    colors_std = [PALETTE["std7"], PALETTE["std30"]]

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.patch.set_facecolor("white")
    ax_mean, ax_std = axes

    # Raw rate on both subplots
    for ax in axes:
        ax.plot(df["date"], df["rate"], color=PALETTE["rate"],
                alpha=0.20, linewidth=0.8, label="Raw rate")

    for w, cm, cs in zip(windows, colors_mean, colors_std):
        rm = df["rate"].rolling(w, min_periods=1).mean()
        rs = df["rate"].rolling(w, min_periods=1).std()

        ax_mean.plot(df["date"], rm, color=cm, linewidth=1.6, label=f"{w}-day mean")
        ax_std.plot(df["date"], rs, color=cs, linewidth=1.4, label=f"{w}-day std")

        ax_mean.fill_between(df["date"], rm - rs, rm + rs, alpha=0.10, color=cm)

    ax_mean.set_title("Rolling Mean with ±1 Std Band", **FONT_TITLE, pad=12)
    ax_mean.set_ylabel("MWK per 1 USD", **FONT_LABEL)
    ax_mean.legend(fontsize=9.5, framealpha=0.75, ncol=3)

    ax_std.set_title("Rolling Standard Deviation (Volatility)", **FONT_TITLE, pad=12)
    ax_std.set_ylabel("Std Dev (MWK)", **FONT_LABEL)
    ax_std.set_xlabel("Date", **FONT_LABEL)
    ax_std.legend(fontsize=9.5, framealpha=0.75, ncol=2)

    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.tick_params(**FONT_TICK)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color(PALETTE["spine"])

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.35)
    out = os.path.join(PLOT_DIR, "rolling_stats.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


def plot_heatmap(df: pd.DataFrame) -> None:
    """Plot correlation heatmap of macroeconomic features."""
    MACRO_COLS = [
        "rate", "Inflation", "Money_Supply", "Foreign_Reserves",
        "Current_Account_Balance", "Lending_Interest_Rate",
        "Real_Interest_Rate", "GDP_Growth", "us_cpi", "us_fed_rate",
        "inflation_diff", "interest_rate_diff",
    ]

    cols = [c for c in MACRO_COLS if c in df.columns]
    sub = df[cols].dropna()
    corr = sub.corr()

    label_map = {
        "rate": "Exchange Rate",
        "Inflation": "Inflation (MW)",
        "Money_Supply": "Money Supply",
        "Foreign_Reserves": "FX Reserves",
        "Current_Account_Balance": "Current Acct Bal",
        "Lending_Interest_Rate": "Lending Rate",
        "Real_Interest_Rate": "Real Interest Rate",
        "GDP_Growth": "GDP Growth",
        "us_cpi": "US CPI",
        "us_fed_rate": "US Fed Rate",
        "inflation_diff": "Inflation Diff",
        "interest_rate_diff": "Interest Rate Diff",
    }

    corr.index = [label_map.get(c, c) for c in corr.index]
    corr.columns = [label_map.get(c, c) for c in corr.columns]

    fig, ax = plt.subplots(figsize=(12, 9))
    fig.patch.set_facecolor("white")

    mask = np.triu(np.ones_like(corr, dtype=bool))
    cmap = sns.diverging_palette(220, 20, as_cmap=True)

    sns.heatmap(
        corr, mask=mask, cmap=cmap, vmin=-1, vmax=1, center=0,
        annot=True, fmt=".2f", annot_kws={"size": 8.5},
        linewidths=0.6, linecolor="#E2E8F0", square=True, ax=ax,
        cbar_kws={"shrink": 0.75, "label": "Pearson r"},
    )

    ax.set_title("Correlation Heatmap — Macroeconomic Features", **FONT_TITLE, pad=14)
    ax.tick_params(axis="x", rotation=40, labelsize=9)
    ax.tick_params(axis="y", rotation=0, labelsize=9)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "heatmap.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


def plot_feature_importance(df: pd.DataFrame) -> None:
    """Plot Random Forest feature importance."""
    FEATURE_COLS = [
        "Inflation", "Money_Supply", "Foreign_Reserves",
        "Current_Account_Balance", "Lending_Interest_Rate",
        "Real_Interest_Rate", "GDP_Growth", "us_cpi",
        "us_fed_rate", "inflation_diff", "interest_rate_diff",
        "lag_1", "lag_7", "lag_30",
    ]

    feat_cols = [c for c in FEATURE_COLS if c in df.columns]
    if not feat_cols:
        print("  [!] No feature columns found for importance plot")
        return

    sub = df[feat_cols + ["rate"]].dropna()
    X = sub[feat_cols].values
    y = sub["rate"].values

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("rf", RandomForestRegressor(
            n_estimators=200, max_depth=10,
            min_samples_leaf=5, random_state=42, n_jobs=-1
        )),
    ])

    model.fit(X, y)
    importances = model.named_steps["rf"].feature_importances_

    feat_df = (
        pd.DataFrame({"feature": feat_cols, "importance": importances})
        .sort_values("importance", ascending=True)
    )

    norm = plt.Normalize(feat_df["importance"].min(), feat_df["importance"].max())
    cmap_ = plt.cm.Blues
    colors = [cmap_(norm(v)) for v in feat_df["importance"]]

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("white")

    bars = ax.barh(feat_df["feature"], feat_df["importance"],
                   color=colors, edgecolor="white", height=0.65)

    for bar, val in zip(bars, feat_df["importance"]):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", ha="left",
                fontsize=8.5, color="#374151")

    ax.set_title("Feature Importance — RandomForest (target: MWK/USD Rate)",
                 **FONT_TITLE, pad=14)
    ax.set_xlabel("Importance (mean decrease in impurity)", **FONT_LABEL)
    ax.tick_params(**FONT_TICK)
    ax.set_xlim(0, feat_df["importance"].max() * 1.18)

    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(PALETTE["spine"])

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "feature_importance.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. DEEPER TIME SERIES ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def run_adf_test(df: pd.DataFrame) -> None:
    """Perform Augmented Dickey-Fuller test on level and first difference."""
    series = df.set_index("date")["rate"].dropna()
    print("\n── ADF Stationarity Test ──")

    for name, s in [("Level", series), ("1st Diff", series.diff().dropna())]:
        try:
            result = adfuller(s, autolag="AIC")
            print(f"  {name}: ADF statistic = {result[0]:.4f}, p-value = {result[1]:.4f}")
            if result[1] < 0.05:
                print(f"    => Stationary at 5% significance (reject H0)")
            else:
                print(f"    => Non-stationary (cannot reject H0)")
        except Exception as e:
            print(f"  {name}: Test failed - {e}")


def plot_acf_pacf(df: pd.DataFrame, lags: int = 40) -> None:
    """Plot ACF and PACF for the rate series."""
    series = df.set_index("date")["rate"].dropna()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    plot_acf(series, lags=lags, ax=axes[0])
    plot_pacf(series, lags=lags, ax=axes[1], method="ywm")

    axes[0].set_title("Autocorrelation (ACF)", **FONT_TITLE)
    axes[1].set_title("Partial Autocorrelation (PACF)", **FONT_TITLE)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "acf_pacf.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


def plot_seasonal_decompose(df: pd.DataFrame, period: int = 365) -> None:
    """Perform classical seasonal decomposition."""
    series = df.set_index("date")["rate"].asfreq("D").fillna(method="ffill")

    try:
        decomp = seasonal_decompose(series, model="additive", period=period)

        fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
        decomp.observed.plot(ax=axes[0], color=PALETTE["rate"])
        axes[0].set_ylabel("Observed", **FONT_LABEL)

        decomp.trend.plot(ax=axes[1], color=PALETTE["mean7"])
        axes[1].set_ylabel("Trend", **FONT_LABEL)

        decomp.seasonal.plot(ax=axes[2], color=PALETTE["std7"])
        axes[2].set_ylabel("Seasonal", **FONT_LABEL)

        decomp.resid.plot(ax=axes[3], color=PALETTE["std30"])
        axes[3].set_ylabel("Residual", **FONT_LABEL)
        axes[3].set_xlabel("Date", **FONT_LABEL)

        fig.suptitle(f"Seasonal Decomposition (period={period} days)", **FONT_TITLE)
        plt.tight_layout()

        out = os.path.join(PLOT_DIR, "seasonal_decompose.png")
        fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"  [✓] Saved  {out}")

    except Exception as e:
        print(f"  [!] Seasonal decomposition failed: {e}")


def detect_regime_changes(df: pd.DataFrame) -> None:
    """Detect structural breaks using PELT algorithm."""
    if not RUPTURES_AVAILABLE:
        print("  [!] ruptures not installed — skipping regime change detection.")
        return

    try:
        series = df.set_index("date")["rate"].dropna().values
        algo = rpt.Pelt(model="l2").fit(series)
        change_points = algo.predict(pen=10)

        fig, ax = plt.subplots(figsize=(14, 4))
        ax.plot(df["date"], df["rate"], color=PALETTE["rate"], lw=1)

        for cp in change_points[:-1]:
            ax.axvline(df["date"].iloc[cp], color="red", linestyle="--", alpha=0.7)

        ax.set_title("Regime Change Detection (PELT)", **FONT_TITLE)
        ax.set_xlabel("Date", **FONT_LABEL)
        ax.set_ylabel("MWK/USD", **FONT_LABEL)

        plt.tight_layout()
        out = os.path.join(PLOT_DIR, "regime_changes.png")
        fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"  [✓] Saved  {out}  (Detected {len(change_points)-1} breakpoints)")

    except Exception as e:
        print(f"  [!] Regime detection failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. MODELLING & FORECASTING
# ══════════════════════════════════════════════════════════════════════════════

def forecast_arima(df: pd.DataFrame, forecast_steps: int = 90) -> None:
    """Generate and plot ARIMA forecast."""
    try:
        series = df.set_index("date")["rate"].asfreq("D").fillna(method="ffill")
        model = ARIMA(series, order=(2, 1, 2))
        fitted = model.fit()
        forecast = fitted.get_forecast(steps=forecast_steps)
        pred_df = forecast.conf_int()
        pred_df["mean"] = forecast.predicted_mean

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.plot(series.index[-365:], series[-365:], label="Historical", color=PALETTE["rate"])
        ax.plot(pred_df.index, pred_df["mean"], label="ARIMA(2,1,2) forecast", color=PALETTE["mean7"])
        ax.fill_between(pred_df.index, pred_df.iloc[:, 0], pred_df.iloc[:, 1],
                        alpha=0.2, color=PALETTE["mean7"])

        ax.set_title("ARIMA 90‑day Forecast", **FONT_TITLE)
        ax.legend()
        ax.set_xlabel("Date", **FONT_LABEL)
        ax.set_ylabel("MWK/USD", **FONT_LABEL)

        plt.tight_layout()
        out = os.path.join(PLOT_DIR, "arima_forecast.png")
        fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"  [✓] Saved  {out}")
        print(f"  ARIMA last value: {series[-1]:.2f}, forecast end: {pred_df['mean'].iloc[-1]:.2f}")

    except Exception as e:
        print(f"  [!] ARIMA forecast failed: {e}")


def forecast_prophet(df: pd.DataFrame) -> None:
    """Generate and plot Prophet forecast."""
    if not PROPHET_AVAILABLE:
        print("  [!] prophet not installed — skipping Prophet forecast.")
        return

    try:
        prophet_df = df[["date", "rate"]].rename(columns={"date": "ds", "rate": "y"})
        prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])

        model = Prophet(
            daily_seasonality=False,
            yearly_seasonality=True,
            changepoint_prior_scale=0.5
        )
        model.fit(prophet_df)

        future = model.make_future_dataframe(periods=90)
        forecast = model.predict(future)

        fig = model.plot(forecast, figsize=(14, 5))
        ax = fig.gca()
        ax.set_title("Prophet Forecast with Uncertainty", **FONT_TITLE)
        ax.set_xlabel("Date", **FONT_LABEL)
        ax.set_ylabel("MWK/USD", **FONT_LABEL)

        out = os.path.join(PLOT_DIR, "prophet_forecast.png")
        fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"  [✓] Saved  {out}")

    except Exception as e:
        print(f"  [!] Prophet forecast failed: {e}")


def compare_model_importances(df: pd.DataFrame) -> None:
    """Compare feature importances across tree-based models."""
    FEATURE_COLS = [
        "Inflation", "Money_Supply", "Foreign_Reserves",
        "Current_Account_Balance", "Lending_Interest_Rate",
        "Real_Interest_Rate", "GDP_Growth", "us_cpi",
        "us_fed_rate", "inflation_diff", "interest_rate_diff"
    ]

    feat_cols = [c for c in FEATURE_COLS if c in df.columns]
    if not feat_cols:
        return

    sub = df[feat_cols + ["rate"]].dropna()
    X, y = sub[feat_cols], sub["rate"]

    # Scale for tree models
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    def get_importances(model, name):
        if name == "RandomForest":
            model.fit(X, y)
            imp = model.feature_importances_
        elif name == "XGBoost":
            if not XGB_AVAILABLE:
                return None
            model.fit(X_scaled, y)
            imp = model.feature_importances_
        elif name == "LightGBM":
            if not LGB_AVAILABLE:
                return None
            model.fit(X_scaled, y)
            imp = model.feature_importances_ / model.feature_importances_.sum()
        return pd.Series(imp, index=feat_cols)

    models = {
        "RandomForest": RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
        "XGBoost": xgb.XGBRegressor(n_estimators=200, random_state=42, verbosity=0) if XGB_AVAILABLE else None,
        "LightGBM": lgb.LGBMRegressor(n_estimators=200, random_state=42, verbose=-1) if LGB_AVAILABLE else None,
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 7), sharey=True)

    for ax, (name, model) in zip(axes, models.items()):
        if model is None:
            ax.text(0.5, 0.5, "Not installed", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(name, **FONT_TITLE)
            continue

        imp = get_importances(model, name)
        if imp is not None:
            imp.sort_values().plot.barh(ax=ax, color=PALETTE["mean7"])
            ax.set_title(name, **FONT_TITLE)
            ax.set_xlabel("Importance")

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "model_importances_comparison.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


def walk_forward_cv(df: pd.DataFrame, n_splits: int = 5) -> None:
    """Perform walk-forward cross-validation."""
    FEATURE_COLS = [
        "Inflation", "Money_Supply", "Foreign_Reserves",
        "Current_Account_Balance", "Lending_Interest_Rate",
        "Real_Interest_Rate", "GDP_Growth", "us_cpi",
        "us_fed_rate", "inflation_diff", "interest_rate_diff",
        "lag_1", "lag_7", "lag_30"
    ]

    feat_cols = [c for c in FEATURE_COLS if c in df.columns]
    if not feat_cols:
        return

    sub = df[feat_cols + ["rate"]].dropna()
    X, y = sub[feat_cols].values, sub["rate"].values

    tscv = TimeSeriesSplit(n_splits=n_splits)
    rmse_list, mae_list = [], []

    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model = RandomForestRegressor(
            n_estimators=200, max_depth=10,
            min_samples_leaf=5, random_state=42, n_jobs=-1
        )
        model.fit(X_train, y_train)
        pred = model.predict(X_test)

        rmse_list.append(np.sqrt(mean_squared_error(y_test, pred)))
        mae_list.append(mean_absolute_error(y_test, pred))

    print("\n── Walk-Forward CV (RandomForest) ──")
    print(f"  RMSE: {np.mean(rmse_list):.2f} ± {np.std(rmse_list):.2f}")
    print(f"  MAE : {np.mean(mae_list):.2f} ± {np.std(mae_list):.2f}")

    # Save scores
    pd.DataFrame({
        "fold": range(1, n_splits + 1),
        "RMSE": rmse_list,
        "MAE": mae_list
    }).to_csv(os.path.join(REPORT_DIR, "walk_forward_cv.csv"), index=False)
    print(f"  [✓] Saved CV scores to {REPORT_DIR}/walk_forward_cv.csv")


# ══════════════════════════════════════════════════════════════════════════════
# 5. STATISTICAL DIAGNOSTICS
# ══════════════════════════════════════════════════════════════════════════════

def outlier_detection(df: pd.DataFrame) -> None:
    """Detect outliers using multiple methods."""
    rate = df["rate"].dropna()

    # IQR method
    q1, q3 = rate.quantile(0.25), rate.quantile(0.75)
    iqr = q3 - q1
    iqr_outliers = ((rate < q1 - 1.5 * iqr) | (rate > q3 + 1.5 * iqr)).sum()

    # Z-score method
    z = np.abs(stats.zscore(rate))
    z_outliers = (z > 3).sum()

    # Isolation Forest
    iso = IsolationForest(contamination=0.05, random_state=42)
    pred = iso.fit_predict(rate.values.reshape(-1, 1))
    if_outliers = (pred == -1).sum()

    # Plot outliers
    outliers_mask = (pred == -1)
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(df["date"], df["rate"], color=PALETTE["rate"], alpha=0.7)
    ax.scatter(
        df["date"][outliers_mask],
        df["rate"][outliers_mask],
        color="red", s=15, label=f"Isolation Forest ({(pred==-1).sum()} pts)"
    )
    ax.set_title("Outlier Detection", **FONT_TITLE)
    ax.legend()

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "outliers.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")
    print(f"  Outliers detected: IQR={iqr_outliers}, Z-score={z_outliers}, IsolationForest={if_outliers}")


def plot_distributions(df: pd.DataFrame) -> None:
    """Plot KDE + histogram for each numeric column."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c != "rate"]

    if not numeric_cols:
        return

    n = len(numeric_cols)
    ncols = 3
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(15, nrows * 3.5))
    axes = axes.flatten()

    for i, col in enumerate(numeric_cols):
        sns.histplot(df[col].dropna(), kde=True, ax=axes[i],
                     color=PALETTE["mean7"], alpha=0.6, edgecolor=None)
        axes[i].set_title(col, fontsize=10, color="#1A2535")
        axes[i].set_xlabel("")
        axes[i].set_ylabel("")

    # Hide unused subplots
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("Feature Distributions (KDE + Histogram)", **FONT_TITLE)
    plt.tight_layout()

    out = os.path.join(PLOT_DIR, "distributions.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


def qq_plot_returns(df: pd.DataFrame) -> None:
    """Generate QQ plot for daily returns."""
    returns = df.set_index("date")["rate"].pct_change().dropna()
    fig = qqplot(returns, line="s")
    ax = fig.gca()
    ax.set_title("QQ‑Plot of Daily Returns", **FONT_TITLE)
    plt.tight_layout()

    out = os.path.join(PLOT_DIR, "qq_returns.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


def granger_causality(df: pd.DataFrame, maxlag: int = 7) -> None:
    """Test Granger causality between inflation and exchange rate changes."""
    rate_diff = df.set_index("date")["rate"].diff().dropna()
    inflation = df.set_index("date")["Inflation"]
    data = pd.concat([rate_diff, inflation], axis=1).dropna()
    data.columns = ["rate_diff", "inflation"]

    print(f"\n── Granger Causality (Inflation → ΔRate) ──")
    try:
        result = grangercausalitytests(data[["rate_diff", "inflation"]],
                                       maxlag=maxlag, verbose=False)
        for lag, res in result.items():
            p_val = res[0]["ssr_ftest"][1]
            print(f"  Lag {lag}: F-test p-value = {p_val:.4f} {'*' if p_val < 0.05 else ''}")
    except Exception as e:
        print(f"  [!] Granger causality test failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. FEATURE ENGINEERING INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════

def plot_lag_correlation(df: pd.DataFrame, max_lag: int = 30) -> None:
    """Plot correlation between macro features and rate at different lags."""
    macro = [c for c in ["Inflation", "Money_Supply", "Foreign_Reserves",
                         "Current_Account_Balance", "Lending_Interest_Rate",
                         "GDP_Growth"] if c in df.columns]

    if not macro:
        return

    rate = df.set_index("date")["rate"]
    results = {}

    for feat in macro:
        series = df.set_index("date")[feat]
        corr_list = []
        for lag in range(0, max_lag + 1):
            corr_list.append(rate.corr(series.shift(lag)))
        results[feat] = corr_list

    plt.figure(figsize=(12, 6))
    for feat, corr in results.items():
        plt.plot(range(0, max_lag + 1), corr, marker=".", label=feat)

    plt.axhline(0, color="black", linewidth=0.5)
    plt.title("Lag Correlation: Macro Features vs Exchange Rate", **FONT_TITLE)
    plt.xlabel("Lag (days)")
    plt.ylabel("Pearson r")
    plt.legend(fontsize=9)

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "lag_correlation.png")
    plt.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close()
    print(f"  [✓] Saved  {out}")


def mutual_information_scores(df: pd.DataFrame) -> None:
    """Compute mutual information between features and rate."""
    FEATURE_COLS = [
        "Inflation", "Money_Supply", "Foreign_Reserves",
        "Current_Account_Balance", "Lending_Interest_Rate",
        "Real_Interest_Rate", "GDP_Growth", "us_cpi",
        "us_fed_rate", "inflation_diff", "interest_rate_diff"
    ]

    feat_cols = [c for c in FEATURE_COLS if c in df.columns]
    if not feat_cols:
        return

    sub = df[feat_cols + ["rate"]].dropna()
    X, y = sub[feat_cols], sub["rate"]

    mi = mutual_info_regression(X, y, random_state=42)
    mi_series = pd.Series(mi, index=feat_cols).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    mi_series.plot.barh(ax=ax, color=PALETTE["mean7"])
    ax.set_title("Mutual Information with Exchange Rate", **FONT_TITLE)
    ax.set_xlabel("Mutual Information Score")

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "mutual_information.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


def dimensionality_reduction(df: pd.DataFrame) -> None:
    """Perform PCA and UMAP for dimensionality reduction visualization."""
    FEATURE_COLS = [
        "Inflation", "Money_Supply", "Foreign_Reserves",
        "Current_Account_Balance", "Lending_Interest_Rate",
        "GDP_Growth", "us_cpi", "us_fed_rate",
        "inflation_diff", "interest_rate_diff"
    ]

    feat_cols = [c for c in FEATURE_COLS if c in df.columns]
    if not feat_cols:
        return

    sub = df[feat_cols + ["rate", "date"]].dropna()
    X = StandardScaler().fit_transform(sub[feat_cols])

    # PCA
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)

    fig, axes = plt.subplots(1, 2 if UMAP_AVAILABLE else 1,
                             figsize=(14 if UMAP_AVAILABLE else 7, 6))

    if not isinstance(axes, np.ndarray):
        axes = [axes]

    # PCA - colour by year
    years = sub["date"].dt.year
    scatter1 = axes[0].scatter(X_pca[:, 0], X_pca[:, 1], c=years,
                               cmap="viridis", alpha=0.7,
                               edgecolor="k", linewidth=0.3)
    axes[0].set_title("PCA Colored by Year", **FONT_TITLE)
    axes[0].set_xlabel("PC1")
    axes[0].set_ylabel("PC2")
    plt.colorbar(scatter1, ax=axes[0], label="Year")

    # UMAP if available
    if UMAP_AVAILABLE and len(axes) > 1:
        reducer = umap.UMAP(random_state=42)
        X_umap = reducer.fit_transform(X)
        scatter2 = axes[1].scatter(X_umap[:, 0], X_umap[:, 1],
                                   c=years, cmap="viridis", alpha=0.7,
                                   edgecolor="k", linewidth=0.3)
        axes[1].set_title("UMAP Colored by Year", **FONT_TITLE)
        plt.colorbar(scatter2, ax=axes[1], label="Year")

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "dimensionality_reduction.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


# ══════════════════════════════════════════════════════════════════════════════
# 7. CALENDAR & REGIME ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def plot_monthly_quarterly_boxplots(df: pd.DataFrame) -> None:
    """Plot monthly and quarterly boxplots."""
    df_copy = df.copy()
    df_copy["month"] = df_copy["date"].dt.month
    df_copy["quarter"] = df_copy["date"].dt.quarter
    df_copy["year"] = df_copy["date"].dt.year

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    sns.boxplot(x="month", y="rate", data=df_copy, ax=axes[0],
                palette="Blues", showfliers=False)
    axes[0].set_title("Monthly Rate Distribution", **FONT_TITLE)
    axes[0].set_xlabel("Month")
    axes[0].set_ylabel("MWK/USD")

    sns.boxplot(x="quarter", y="rate", data=df_copy, ax=axes[1],
                palette="Blues", showfliers=False)
    axes[1].set_title("Quarterly Rate Distribution", **FONT_TITLE)
    axes[1].set_xlabel("Quarter")
    axes[1].set_ylabel("MWK/USD")

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "calendar_boxplots.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


def pegged_vs_nonpegged(df: pd.DataFrame) -> None:
    """Compare pegged vs non-pegged regime distributions."""
    if "is_pegged_regime" not in df.columns:
        print("  [!] 'is_pegged_regime' column not found — skipping regime comparison.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    df_copy = df.copy()
    df_copy["period"] = np.where(df_copy["is_pegged_regime"] == 1,
                                 "Pegged", "Non‑pegged")

    sns.boxplot(x="period", y="rate", data=df_copy,
                palette="Set2", showfliers=False, ax=ax)

    ax.set_title("Exchange Rate: Pegged vs Non‑pegged Regimes", **FONT_TITLE)
    ax.set_xlabel("")
    ax.set_ylabel("MWK/USD")

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "pegged_regime_comparison.png")
    fig.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [✓] Saved  {out}")


def year_over_year_heatmap(df: pd.DataFrame) -> None:
    """Generate YoY rate change heatmap."""
    df_copy = df.copy()
    df_copy["year"] = df_copy["date"].dt.year
    df_copy["month"] = df_copy["date"].dt.month

    # Last available rate per month
    monthly_end = df_copy.groupby(["year", "month"])["rate"].last().unstack(level=0)

    # Calculate YoY changes
    results = pd.DataFrame(index=monthly_end.index, columns=monthly_end.columns)
    for yr in monthly_end.columns:
        prev_yr = yr - 1
        if prev_yr in monthly_end.columns:
            results[yr] = (monthly_end[yr] / monthly_end[prev_yr] - 1) * 100

    # Transpose for year on x-axis
    results = results.T

    plt.figure(figsize=(14, 6))
    sns.heatmap(results, annot=True, fmt=".1f", cmap="RdBu", center=0,
                linewidths=0.5, cbar_kws={"label": "YoY % change"})

    plt.title("Year‑over‑Year Rate Change Heatmap (Month × Year)", **FONT_TITLE)
    plt.xlabel("Month")
    plt.ylabel("Year")

    plt.tight_layout()
    out = os.path.join(PLOT_DIR, "yoy_heatmap.png")
    plt.savefig(out, dpi=FIG_DPI, bbox_inches="tight")
    plt.close()
    print(f"  [✓] Saved  {out}")


# ══════════════════════════════════════════════════════════════════════════════
# 8. REPORTING
# ══════════════════════════════════════════════════════════════════════════════

def export_stats_summary(df: pd.DataFrame) -> None:
    """Export key statistics to CSV."""
    stats_dict = {
        "start_date": df["date"].min(),
        "end_date": df["date"].max(),
        "num_rows": len(df),
        "rate_min": df["rate"].min(),
        "rate_max": df["rate"].max(),
        "rate_mean": df["rate"].mean(),
        "rate_std": df["rate"].std(),
        "total_depreciation_pct": (df["rate"].iloc[-1] / df["rate"].iloc[0] - 1) * 100,
    }

    # Add ADF test results
    try:
        adf_result = adfuller(df.set_index("date")["rate"].dropna())
        stats_dict["adf_statistic"] = adf_result[0]
        stats_dict["adf_pvalue"] = adf_result[1]
    except:
        pass

    # Add column statistics
    for col in df.select_dtypes(include=[np.number]).columns:
        stats_dict[f"{col}_mean"] = df[col].mean()
        stats_dict[f"{col}_std"] = df[col].std()
        stats_dict[f"{col}_missing"] = df[col].isnull().sum()

    pd.DataFrame([stats_dict]).to_csv(
        os.path.join(REPORT_DIR, "statistics_summary.csv"), index=False
    )
    print(f"  [✓] Statistics summary saved to {REPORT_DIR}/statistics_summary.csv")


def generate_pdf_report() -> None:
    """Combine all PNG files into a single PDF report."""
    try:
        from PIL import Image

        png_files = sorted([f for f in os.listdir(PLOT_DIR) if f.endswith(".png")])
        if not png_files:
            print("  No plots to compile into PDF.")
            return

        images = []
        for f in png_files:
            img = Image.open(os.path.join(PLOT_DIR, f)).convert("RGB")
            images.append(img)

        pdf_path = os.path.join(REPORT_DIR, "eda_report.pdf")
        if images:
            images[0].save(pdf_path, save_all=True, append_images=images[1:])
            print(f"  [✓] PDF report saved to {pdf_path}")
    except ImportError:
        print("  [!] PIL not installed — skipping PDF generation.")
    except Exception as e:
        print(f"  [!] PDF generation failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Run the complete EDA pipeline."""
    df = load_data(DATA_PATH)

    print("  Generating original EDA plots …\n")
    plot_time_series(df)
    plot_rolling_stats(df)
    plot_heatmap(df)
    plot_feature_importance(df)

    print("\n── Deeper Time Series Analysis ──")
    run_adf_test(df)
    plot_acf_pacf(df)
    plot_seasonal_decompose(df)
    detect_regime_changes(df)

    print("\n── Modelling & Forecasting ──")
    forecast_arima(df)
    forecast_prophet(df)
    compare_model_importances(df)
    walk_forward_cv(df)

    print("\n── Statistical Diagnostics ──")
    outlier_detection(df)
    plot_distributions(df)
    qq_plot_returns(df)
    granger_causality(df)

    print("\n── Feature Engineering Insights ──")
    plot_lag_correlation(df)
    mutual_information_scores(df)
    dimensionality_reduction(df)

    print("\n── Calendar & Regime Analysis ──")
    plot_monthly_quarterly_boxplots(df)
    pegged_vs_nonpegged(df)
    year_over_year_heatmap(df)

    print("\n── Reporting ──")
    export_stats_summary(df)
    generate_pdf_report()

    print(f"\n  ✅ All outputs saved to {PLOT_DIR}/ and {REPORT_DIR}/\n")


if __name__ == "__main__":
    main()