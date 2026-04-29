import sys
import os
import pandas as pd

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
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add root AND backend to Python path
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

# ---------------------------------------------------------
# 📦 SAFE LOGGER SETUP
# ---------------------------------------------------------
try:
    from core.logging_config import get_logger
    logger = get_logger(__name__)
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("⚠️ Using fallback logger")

# ---------------------------------------------------------
# 📥 IMPORT PIPELINE COMPONENTS
# ---------------------------------------------------------
from ml.pipeline.macro_fetcher import merge_and_process_macro
from ml.pipeline.master_pipeline import run_pipeline

# ---------------------------------------------------------
# 📁 MODEL SAVE LOCATION
# ---------------------------------------------------------
if IS_COLAB:
    MODEL_DIR = "/content/models"
else:
    MODEL_DIR = os.path.join(ROOT_DIR, "backend", "ml", "artifacts")

os.makedirs(MODEL_DIR, exist_ok=True)

# Make it accessible inside pipeline
os.environ["MODEL_DIR"] = MODEL_DIR

logger.info(f"📦 Model directory set to: {MODEL_DIR}")

# ---------------------------------------------------------
# 🚀 MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    try:
        # -------------------------------------------------
        # STEP 1: Fetch Macro Data (SAFE MODE IN COLAB)
        # -------------------------------------------------
        logger.info("🌐 Step 1: Macro Data Fetch...")

        three_years_ago = (
            pd.Timestamp.now() - pd.Timedelta(days=365 * 3)
        ).strftime("%Y-%m-%d")

        if IS_COLAB:
            logger.info("⏭️ Skipping macro fetch in Colab (using existing data)")
        else:
            try:
                merge_and_process_macro(three_years_ago)
                logger.info("✅ Macro Data Fetch Complete.")
            except Exception as e:
                logger.error(f"⚠️ Macro fetch failed: {e}")
                logger.info("⚠️ Proceeding with existing DB data...")

        # -------------------------------------------------
        # STEP 2: RUN TRAINING PIPELINE
        # -------------------------------------------------
        logger.info("🤖 Step 2: Running Model Training Pipeline...")

        run_pipeline()

        # -------------------------------------------------
        # STEP 3: SUCCESS MESSAGE
        # -------------------------------------------------
        logger.info("🎉 Retraining Successful. Models updated.")

        if IS_COLAB:
            logger.info("📥 Download models from: /content/models")

    except Exception as e:
        logger.error(f"💥 Crash in retrain_models.py: {e}")

        import traceback
        traceback.print_exc()
