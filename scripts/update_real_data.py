import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

import pandas as pd
import numpy as np
from ml.pipeline.loader import load_csv
from ml.pipeline.cleaner import clean_data
from ml.pipeline.feature_engineer import engineer_features
from ml.pipeline.db_seeder import seed_exchange_rates, seed_macro_indicators
from ml.pipeline.live_fetcher import fetch_real_rates_yfinance
from core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def update_with_real_data():
    logger.info("=" * 55)
    logger.info("UPDATING DATABASE WITH REAL DATA")
    logger.info("=" * 55)

    # Step 1 — Load and clean original CSV (up to Nov 2024)
    df_csv = load_raw_csv()
    df_csv = clean_data(df_csv)
    logger.info(f"CSV data: {len(df_csv)} rows up to {df_csv['date'].max().date()}")

    # Step 2 — Fetch real rates from Yahoo Finance
    df_real = fetch_real_rates_yfinance()

    if df_real is not None and len(df_real) > 0:
        # Only keep dates after the CSV ends
        csv_end = df_csv["date"].max()
        df_new  = df_real[df_real["date"] > csv_end].copy()
        logger.info(f"New real rows to add: {len(df_new)}")

        if len(df_new) > 0:
            # Forward fill macro columns from last known CSV values
            last_row   = df_csv.iloc[-1]
            macro_cols = [
                "Inflation", "Money_Supply", "Foreign_Reserves",
                "Current_Account_Balance", "Lending_Interest_Rate",
                "Real_Interest_Rate", "GDP_Growth", "us_cpi",
                "us_cpi_yoy", "us_fed_rate", "inflation_diff",
                "interest_rate_diff", "Population"
            ]
            for col in macro_cols:
                if col in df_csv.columns:
                    df_new[col] = last_row.get(col, np.nan)

            df_new["is_interpolated"] = False
            df_new["daily_return"]    = df_new["rate"].pct_change() * 100

            # Combine CSV + real data
            df_combined = pd.concat([df_csv, df_new], ignore_index=True)
            df_combined.sort_values("date", inplace=True)
            df_combined.reset_index(drop=True, inplace=True)
            logger.info(f"Combined: {len(df_combined)} rows | "
                        f"up to {df_combined['date'].max().date()}")
        else:
            logger.info("No new dates beyond CSV — using CSV data only")
            df_combined = df_csv
    else:
        logger.warning("Could not fetch real data — using CSV with gap fill")
        from ml.pipeline.gap_filler import fill_gap
        df_combined = fill_gap(df_csv)

    # Step 3 — Engineer features
    df_final = engineer_features(df_combined)

    # Step 4 — Save processed CSV
    out_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../data/processed/mwk_usd_clean.csv")
    )
    df_final.to_csv(out_path, index=False)
    logger.info(f"Processed CSV saved: {out_path}")
    logger.info(f"Latest date in dataset: {df_final['date'].max().date()}")
    logger.info(f"Latest rate: {df_final['rate'].iloc[-1]:.2f} MWK")

    # Step 5 — Reseed database
    seed_exchange_rates(df_final)
    seed_macro_indicators(df_final)

    logger.info("=" * 55)
    logger.info("REAL DATA UPDATE COMPLETE")
    logger.info("=" * 55)
    return df_final


if __name__ == "__main__":
    update_with_real_data()