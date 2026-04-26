import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

import pytest
import pandas as pd
from ml.pipeline.loader           import load_raw_csv
from ml.pipeline.cleaner          import clean_data
from ml.pipeline.gap_filler       import fill_gap
from ml.pipeline.feature_engineer import engineer_features


def test_loader_reads_csv():
    df = load_raw_csv()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 3000
    assert "date" in df.columns
    assert "rate" in df.columns
    print(f"\n  Loaded {len(df)} rows")


def test_loader_date_range():
    df = load_raw_csv()
    assert df["date"].min().year == 2013
    assert df["date"].max().year >= 2024


def test_cleaner_removes_duplicates():
    df = load_raw_csv()
    cleaned = clean_data(df)
    assert cleaned["date"].duplicated().sum() == 0


def test_cleaner_no_negative_rates():
    df = load_raw_csv()
    cleaned = clean_data(df)
    assert (cleaned["rate"] > 0).all()


def test_cleaner_no_weekends():
    df = load_raw_csv()
    cleaned = clean_data(df)
    assert (cleaned["date"].dt.dayofweek < 5).all()


def test_gap_filler_covers_today():
    df = load_raw_csv()
    df = clean_data(df)
    filled = fill_gap(df)
    last_date = filled["date"].max()
    assert str(last_date.date()) >= "2026-04-17"
    print(f"\n  Gap filled to: {last_date.date()}")


def test_gap_filler_no_weekends():
    df = load_raw_csv()
    df = clean_data(df)
    filled = fill_gap(df)
    gap_rows = filled[filled["is_interpolated"] == True]
    assert (gap_rows["date"].dt.dayofweek < 5).all()


def test_feature_engineer_adds_lags():
    df = load_raw_csv()
    df = clean_data(df)
    df = fill_gap(df)
    df = engineer_features(df)
    assert "lag_1"  in df.columns
    assert "lag_7"  in df.columns
    assert "lag_30" in df.columns


def test_feature_engineer_adds_rolling():
    df = load_raw_csv()
    df = clean_data(df)
    df = fill_gap(df)
    df = engineer_features(df)
    assert "rolling_mean_7"  in df.columns
    assert "rolling_mean_30" in df.columns
    assert "rolling_std_30"  in df.columns


def test_feature_engineer_no_nulls_in_key_cols():
    df = load_raw_csv()
    df = clean_data(df)
    df = fill_gap(df)
    df = engineer_features(df)
    for col in ["lag_1", "lag_7", "rolling_mean_30"]:
        assert df[col].isnull().sum() == 0, f"{col} has nulls"