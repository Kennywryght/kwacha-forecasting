import os
from db.database import SessionLocal
from db.models import ModelRun
from datetime import datetime

def ensure_dirs():
    paths = [
        "outputs/metrics",
        "outputs/plots",
        "ml/artifacts"
    ]

    for p in paths:
        os.makedirs(p, exist_ok=True)
        



def log_model_run(model_name, metrics):

    db = SessionLocal()

    try:
        run = ModelRun(
            model_name=model_name,
            rmse=metrics.get("rmse"),
            mae=metrics.get("mae"),
            mape=metrics.get("mape"),
            r_squared=metrics.get("r_squared"),
            trained_at=datetime.utcnow()
        )

        db.add(run)
        db.commit()

    finally:
        db.close()