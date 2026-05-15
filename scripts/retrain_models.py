import sys
import os

# ---------------------------------------------------------
# 🌍 ENV DETECTION (Colab vs Local)
# ---------------------------------------------------------
IS_COLAB = "COLAB_GPU" in os.environ

if IS_COLAB:
    print("🚀 Running in Google Colab")
else:
    print("💻 Running locally")

# ---------------------------------------------------------
# 🧠 PATH SETUP (FIXES: No module named 'ml')
# ---------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')

# Add both root and backend so that imports like 'backend.ml' and 'ml' work
for d in [ROOT_DIR, BACKEND_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

print(f"DEBUG: ROOT_DIR = {ROOT_DIR}")
print(f"DEBUG: BACKEND_DIR = {BACKEND_DIR}")
print(f"DEBUG: sys.path has backend = {BACKEND_DIR in sys.path}")

# ---------------------------------------------------------
# 📁 MODEL SAVE LOCATION
# ---------------------------------------------------------
if IS_COLAB:
    MODEL_DIR = "/content/models"
else:
    MODEL_DIR = os.path.join(ROOT_DIR, "backend", "ml", "artifacts")

os.makedirs(MODEL_DIR, exist_ok=True)
os.environ["MODEL_DIR"] = MODEL_DIR

print(f"✅ Model directory set to: {MODEL_DIR}")

# ---------------------------------------------------------
# 📦 SAFE LOGGER SETUP
# ---------------------------------------------------------
try:
    from backend.core.logging_config import get_logger
    logger = get_logger(__name__)
    print("✅ Logger initialized")
except Exception as e:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    print(f"⚠️ Using fallback logger: {e}")

# ---------------------------------------------------------
# 📥 IMPORT PIPELINE COMPONENTS
# ---------------------------------------------------------
try:
    from backend.ml.pipeline.master_pipeline import run_pipeline
    from backend.ml.pipeline.full_pipeline import run_full_pipeline
    print("✅ Pipeline modules imported successfully")
except Exception as e:
    print(f"❌ Failed to import pipeline modules: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------------
# 🚀 MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true",
                        help="Run full pipeline (training + tuning + explainability)")
    args = parser.parse_args()

    try:
        if args.full:
            logger.info("🌟 Running FULL pipeline (data update + base training + tuning + SHAP)...")
            run_full_pipeline()
        else:
            logger.info("📊 Running base training pipeline only...")
            run_pipeline()

        logger.info("🎉 Pipeline completed successfully.")

        if IS_COLAB:
            logger.info("📥 You can now download results from /content/models and outputs/")

    except Exception as e:
        logger.error(f"💥 Crash in retrain_models.py: {e}")
        import traceback
        traceback.print_exc()