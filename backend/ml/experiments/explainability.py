import os
import pandas as pd
import numpy as np
import shap
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor

# -----------------------------
# CONFIG
# -----------------------------
DATA_PATH = "data/processed/mwk_usd_clean.csv"
OUTPUT_DIR = "outputs/shap"
TARGET_COLUMN = "rate"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# -----------------------------
# LOAD DATA
# -----------------------------
def load_data():
    df = pd.read_csv(DATA_PATH)

    print("\n📊 Available columns:", df.columns.tolist())

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"❌ Target column '{TARGET_COLUMN}' not found")

    # Keep only numeric columns
    df = df.select_dtypes(include=[np.number])

    X = df.drop(columns=[TARGET_COLUMN])
    y = df[TARGET_COLUMN]

    print(f"✅ Using target column: {TARGET_COLUMN}")
    print(f"📈 Features used: {list(X.columns)}")

    return X, y


# -----------------------------
# TRAIN MODEL
# -----------------------------
def train_model(X, y):
    split_idx = int(len(X) * 0.8)

    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    print("✅ Model trained successfully")

    return model, X_test


# -----------------------------
# SHAP COMPUTATION
# -----------------------------
def compute_shap(model, X_sample):
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    return explainer, shap_values


# -----------------------------
# SAVE PLOTS
# -----------------------------
def save_summary_plots(shap_values, X_sample):
    # Summary plot
    plt.figure()
    shap.summary_plot(shap_values, X_sample, show=False)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/shap_summary.png")
    plt.close()

    # Feature importance (bar)
    plt.figure()
    shap.summary_plot(shap_values, X_sample, plot_type="bar", show=False)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/shap_feature_importance.png")
    plt.close()

    print("📊 SHAP summary plots saved")


# -----------------------------
# FORCE PLOT (🔥 EXTRA EDGE)
# -----------------------------
def save_force_plot(explainer, shap_values, X_sample):
    sample_index = 0

    shap.force_plot(
        explainer.expected_value,
        shap_values[sample_index],
        X_sample.iloc[sample_index],
        matplotlib=True,
        show=False
    )

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/shap_force_plot.png")
    plt.close()

    print("🔥 SHAP force plot saved")


# -----------------------------
# INTERPRETATION
# -----------------------------
def interpret_features(shap_values, X_sample):
    print("\n🔍 SHAP FEATURE INTERPRETATION\n")

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    feature_importance = pd.Series(mean_abs_shap, index=X_sample.columns)
    feature_importance = feature_importance.sort_values(ascending=False)

    top_features = feature_importance.head(5)

    for feature, value in top_features.items():
        print(f"Feature: {feature}")
        print(f"Impact Strength: {value:.4f}")

        # Direction
        corr = np.corrcoef(
            X_sample[feature],
            shap_values[:, X_sample.columns.get_loc(feature)]
        )[0, 1]

        if corr > 0:
            print("Effect: Higher values increase exchange rate")
        else:
            print("Effect: Higher values decrease exchange rate")

        print("-" * 40)


# -----------------------------
# MAIN
# -----------------------------
def main():
    print("🚀 Running SHAP Explainability...\n")

    X, y = load_data()
    model, X_test = train_model(X, y)

    # Sample for speed
    X_sample = X_test.sample(min(100, len(X_test)), random_state=42)

    explainer, shap_values = compute_shap(model, X_sample)

    save_summary_plots(shap_values, X_sample)
    save_force_plot(explainer, shap_values, X_sample)
    interpret_features(shap_values, X_sample)

    print("\n✅ SHAP analysis complete.")
    print(f"📁 Results saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()