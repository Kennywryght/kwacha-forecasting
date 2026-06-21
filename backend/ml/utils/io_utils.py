"""Input/Output utilities for the forecasting pipeline.

This module provides helper functions for directory management,
file operations, and database logging.
"""

import os
import json
import pickle
from typing import Dict, Any, Optional
from datetime import datetime

from db.database import SessionLocal
from db.models import ModelRun


def ensure_dirs() -> None:
    """
    Ensure all required directories exist.
    """
    paths = [
        "outputs/metrics",
        "outputs/plots",
        "outputs/explain",
        "outputs/tuning",
        "ml/artifacts",
        "ml/experiments",
        "data/raw",
        "data/processed"
    ]
    
    for p in paths:
        os.makedirs(p, exist_ok=True)


def log_model_run(
    model_name: str,
    metrics: Dict[str, float],
    params: Optional[Dict[str, Any]] = None
) -> Optional[int]:
    """
    Log model run results to database.

    Args:
        model_name: Name of the model
        metrics: Dictionary of metrics
        params: Optional model parameters

    Returns:
        ID of the created record, or None if failed
    """
    db = SessionLocal()
    
    try:
        run = ModelRun(
            model_name=model_name,
            rmse=metrics.get("rmse"),
            mae=metrics.get("mae"),
            mape=metrics.get("mape"),
            r_squared=metrics.get("r_squared"),
            trained_at=datetime.utcnow(),
            params=json.dumps(params) if params else None
        )
        
        db.add(run)
        db.commit()
        db.refresh(run)
        
        return run.id
        
    except Exception as e:
        db.rollback()
        print(f"Failed to log model run: {e}")
        return None
        
    finally:
        db.close()


def save_json(data: Dict[str, Any], filepath: str) -> None:
    """
    Save data as JSON file.

    Args:
        data: Dictionary to save
        filepath: Output file path
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(filepath: str) -> Dict[str, Any]:
    """
    Load JSON file.

    Args:
        filepath: Input file path

    Returns:
        Loaded dictionary
    """
    with open(filepath, "r") as f:
        return json.load(f)


def save_pickle(obj: Any, filepath: str) -> None:
    """
    Save object using pickle.

    Args:
        obj: Object to save
        filepath: Output file path
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        pickle.dump(obj, f)


def load_pickle(filepath: str) -> Any:
    """
    Load object from pickle file.

    Args:
        filepath: Input file path

    Returns:
        Loaded object
    """
    with open(filepath, "rb") as f:
        return pickle.load(f)