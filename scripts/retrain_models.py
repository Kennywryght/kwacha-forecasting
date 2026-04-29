import sys
import os
import pandas as pd

# Ensure the script can import backend modules from the root directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# NEW: Import the macro fetcher we just built
from ml.pipeline.macro_fetcher import merge_and_process_macro
from ml.pipeline.master_pipeline import run_pipeline
from core.logging_config import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    try:
        # ---------------------------------------------------------
        # STEP 1: Fetch Fresh Macro Data (US Fed Rate + Malawi WB)
        # ---------------------------------------------------------
        logger.info("🌐 Step 1: Fetching Macro Data (US Fed + Malawi World Bank)...")
        
        # Calculate start date (last 3 years) to ensure we have enough history for models
        three_years_ago = (pd.Timestamp.now() - pd.Timedelta(days=365*3)).strftime("%Y-%m-%d")
        
        # This will fetch from FRED/World Bank and save to your DB
        try:
            merge_and_process_macro(three_years_ago)
            logger.info("✅ Macro Data Fetch Complete.")
        except Exception as e:
            logger.error(f"⚠️ Macro fetch failed (network/dependency issue): {e}")
            logger.info("⚠️ Proceeding to training with existing DB data (if any)...")

        # ---------------------------------------------------------
        # STEP 2: Run the Training Pipeline
        # ---------------------------------------------------------
        logger.info("🤖 Step 2: Running Model Training Pipeline...")
        
        run_pipeline()
        
        logger.info("🎉 Retraining Successful. Models are updated.")

    except Exception as e:
        logger.error(f"💥 Crash in retrain_models.py: {e}")
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()