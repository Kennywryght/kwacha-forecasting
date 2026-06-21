"""Database logging utilities for model runs.

This module provides functions for logging model performance
to the database for tracking and monitoring.
"""

from db.database import SessionLocal
from db.models import ModelRun
from datetime import datetime
from typing import Dict, Any, Optional
import json


def log_model_run(
    model_name: str,
    metrics: Dict[str, float],
    params: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None
) -> Optional[int]:
    """
    Log model run results to database.

    Args:
        model_name: Name of the model
        metrics: Dictionary of metrics
        params: Optional model parameters
        notes: Optional notes about the run

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
            params=json.dumps(params) if params else None,
            notes=notes
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


def get_latest_model_runs(
    model_name: Optional[str] = None,
    limit: int = 10
) -> list:
    """
    Get the latest model runs from database.

    Args:
        model_name: Filter by model name (optional)
        limit: Maximum number of records to return

    Returns:
        List of ModelRun objects
    """
    db = SessionLocal()
    
    try:
        query = db.query(ModelRun)
        
        if model_name:
            query = query.filter(ModelRun.model_name == model_name)
        
        runs = query.order_by(ModelRun.trained_at.desc()).limit(limit).all()
        return runs
        
    except Exception as e:
        print(f"Failed to get model runs: {e}")
        return []
        
    finally:
        db.close()


def get_best_model() -> Optional[Dict[str, Any]]:
    """
    Get the best performing model from database.

    Returns:
        Dictionary with model info, or None if not found
    """
    db = SessionLocal()
    
    try:
        # Get model with lowest RMSE
        best_run = db.query(ModelRun).order_by(
            ModelRun.rmse.asc()
        ).first()
        
        if best_run is None:
            return None
        
        return {
            "id": best_run.id,
            "model_name": best_run.model_name,
            "rmse": best_run.rmse,
            "mae": best_run.mae,
            "mape": best_run.mape,
            "r_squared": best_run.r_squared,
            "trained_at": best_run.trained_at,
            "params": json.loads(best_run.params) if best_run.params else None
        }
        
    except Exception as e:
        print(f"Failed to get best model: {e}")
        return None
        
    finally:
        db.close()