import os
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db import crud

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("/performance")
def get_model_performance(db: Session = Depends(get_db)):
    # First try the saved metrics JSON (from pretrain.py evaluation)
    metrics_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'ml', 'artifacts', 'model_metrics.json'
    )
    
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            metrics = json.load(f)
        
        models_list = []
        for name, m in metrics.items():
            models_list.append({
                "model_name": name,
                "mape": m.get("mape"),
                "rmse": m.get("rmse"),
                "mae": m.get("mae"),
                "r_squared": m.get("r2", m.get("r_squared")),
            })
        
        if models_list:
            return {"models": models_list}
    
    # Fallback: try database model_runs
    runs = crud.get_active_model_runs(db)
    if runs:
        return {
            "models": [
                {
                    "model_name":  r.model_name,
                    "rmse":        r.rmse,
                    "mae":         r.mae,
                    "mape":        r.mape,
                    "r_squared":   r.r_squared,
                    "trained_at":  str(r.trained_at) if r.trained_at else None,
                }
                for r in runs
            ]
        }
    
    # Nothing found
    return {"models": []}

@router.get("/health")
def get_models_health():
    """Check which models are loaded and their status."""
    from api.routes.forecasts import _models
    return {
        "total_loaded": len(_models),
        "models": {
            name: {
                "is_fitted": m.get("is_fitted", getattr(m, 'is_fitted', False)) if isinstance(m, dict) else getattr(m, 'is_fitted', False)
            }
            for name, m in _models.items()
        }
    }