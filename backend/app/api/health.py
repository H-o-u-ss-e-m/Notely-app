from fastapi import APIRouter
from app.core.config import settings
from app.core.device import get_optimal_device
from app.ml.trocr_engine import trocr_engine
from app.db.session import check_db_connection

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Vérifie l'état du serveur : PostgreSQL, modèle TrOCR, version.
    """
    device = get_optimal_device()
    model_loaded = trocr_engine.model is not None
    db_ok = check_db_connection()

    return {
        "status": "online" if db_ok else "degraded",
        "version": settings.VERSION,
        "device": device,
        "model": settings.TROCR_MODEL,
        "modelLoaded": model_loaded,
        "database": "postgresql:ok" if db_ok else "postgresql:error",
        "firebase": "disabled"
    }
