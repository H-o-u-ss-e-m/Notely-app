"""
main.py — Point d'entrée FastAPI.
PostgreSQL (SQLAlchemy) remplace Firebase/Firestore.
"""
import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse, PlainTextResponse
from fastapi import Depends

# Charger les variables d'environnement (.env)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.body_limit import BodySizeLimitMiddleware
from app.core.errors import register_error_handlers
from app.core.request_context import RequestIdMiddleware
from app.core.ratelimit import limiter, rate_limit_handler
from slowapi.errors import RateLimitExceeded
from app.core.device import get_optimal_device
from app.ml.trocr_engine import trocr_engine
from app.db.session import check_db_connection
from app.db.base import Base
from app.db.session import engine
# Import des modèles pour qu'ils soient connus avant create_all
import app.db.models.user
import app.db.models.course
import app.db.models.ocr_correction
import app.db.models.ocr_correction

setup_logging()
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    device = get_optimal_device()
    logger.info("=" * 70)
    logger.info("  DÉMARRAGE NOTELY — Backend FastAPI + PostgreSQL")
    logger.info(f"  Dispositif cible  : {device.upper()}")
    logger.info(f"  Modèle TrOCR      : {settings.TROCR_MODEL}")
    logger.info(f"  Version API       : {settings.API_V1_STR}")
    logger.info("=" * 70)

    # Vérification connexion PostgreSQL
    if check_db_connection():
        logger.info("✅ PostgreSQL connecté avec succès.")
        # Créer les tables si elles n'existent pas encore (mode dev sans Alembic)
        # create_all UNIQUEMENT en dev (confort). Staging/prod : `alembic upgrade head` obligatoire.
        if settings.ENV == "dev":
            Base.metadata.create_all(bind=engine, checkfirst=True)
    else:
        logger.error("❌ PostgreSQL INDISPONIBLE — L'application ne peut pas démarrer sans base de données.")
        raise RuntimeError("PostgreSQL inaccessible. Vérifiez la variable DATABASE_URL et que PostgreSQL est démarré.")

    # Chargement du moteur TrOCR
    try:
        trocr_engine.load_model()
    except Exception as e:
        logger.warning(f"Préchargement TrOCR différé : {e}")

    yield
    logger.info("Arrêt du backend FastAPI.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=None if settings.ENV == "prod" else "/docs/openapi.json",
    docs_url=None if settings.ENV == "prod" else "/docs",
    lifespan=lifespan
)

# Rate Limiting (SEC-6 : slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Configuration CORS — En dev, autorise tous les ports locaux (Flutter Web/Edge, Angular)
cors_kwargs = {
    "allow_origins": settings.CORS_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["*"],
    "max_age": 3600,
}
if settings.ENV == "dev":
    cors_kwargs["allow_origin_regex"] = r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$"

app.add_middleware(CORSMiddleware, **cors_kwargs)

# Limite de taille des corps de requête (anti-DoS)
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.MAX_REQUEST_BODY_MB * 1024 * 1024)

# Middleware de contrôle de version minimale du client (MLOps / §9.4)
MIN_SUPPORTED_CLIENT_VERSION = getattr(settings, "MIN_CLIENT_VERSION", "1.0.0")

@app.middleware("http")
async def client_version_check_middleware(request: Request, call_next):
    client_version = request.headers.get("X-Client-Version")
    if client_version and client_version < MIN_SUPPORTED_CLIENT_VERSION:
        return JSONResponse(
            status_code=426,
            content={"detail": "Mise à jour requise. Votre version de l'application n'est plus supportée."},
            headers={"X-Min-Client-Version": MIN_SUPPORTED_CLIENT_VERSION}
        )
    response = await call_next(request)
    response.headers["X-Min-Client-Version"] = MIN_SUPPORTED_CLIENT_VERSION
    return response

# Erreurs uniformes + request_id (middleware ajoute en dernier = le plus externe)
register_error_handlers(app)
app.add_middleware(RequestIdMiddleware)

# ── Importation des routeurs ─────────────────────────────────────────────────
from app.api.health import router as health_router
from app.api.recognition import router as recognition_router
from app.api.segmentation import router as segmentation_router
from app.api.documents import router as documents_router
from app.api.ocr_feedback import router as ocr_feedback_router
from app.api.ocr_jobs import router as ocr_jobs_router
from app.api.me import router as me_router
from app.api.models_admin import router as models_admin_router
from app.api.flashcards import router as flashcards_router

# Nouveaux routeurs PostgreSQL (remplacent les anciens Firebase)
from app.modules.auth.router import router as auth_router
from app.modules.courses.router import router as courses_router

# Routes versionnées /api/v1
app.include_router(health_router,       prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(auth_router,         prefix=settings.API_V1_STR, tags=["Authentication"])
app.include_router(recognition_router,  prefix=settings.API_V1_STR, tags=["Recognition"])
app.include_router(ocr_jobs_router,     prefix=settings.API_V1_STR, tags=["OCR Jobs"])
app.include_router(segmentation_router, prefix=settings.API_V1_STR, tags=["Segmentation"])
app.include_router(documents_router,    prefix=settings.API_V1_STR, tags=["Documents"])
app.include_router(courses_router,      prefix=settings.API_V1_STR, tags=["Courses"])
app.include_router(ocr_feedback_router, prefix=settings.API_V1_STR, tags=["OCR Feedback"])
app.include_router(me_router,           prefix=settings.API_V1_STR, tags=["RGPD & Profil"])
app.include_router(flashcards_router,   prefix=settings.API_V1_STR, tags=["Flashcards"])
app.include_router(models_admin_router, prefix=settings.API_V1_STR, tags=["MLOps - Modèles"])

# Routes legacy (compatibilité)
app.include_router(recognition_router,  prefix="/api", tags=["Legacy Recognition"])
app.include_router(segmentation_router, prefix="/api", tags=["Legacy Segmentation"])

# ── Métriques Prometheus & Surveillance IA (§9.3) ───────────────────────────
from app.core.metrics import metrics_collector
from app.domain.confusion_matrix import compute_char_confusions
from app.db.session import get_db
from app.db.models.ocr_correction import OcrCorrection

@app.get("/metrics", response_class=PlainTextResponse, tags=["Monitoring"])
def prometheus_metrics():
    """Exposition des métriques qualité IA et performance au format Prometheus (§9.3)."""
    return metrics_collector.generate_prometheus_text()

@app.get("/api/v1/ocr/confusions", tags=["MLOps - Modèles"])
def get_ocr_confusions(top_k: int = 30, db = Depends(get_db)):
    """Top 30 des confusions de caractères observées sur les corrections (§8.5.d / §9.3)."""
    try:
        rows = db.query(OcrCorrection.predicted_text, OcrCorrection.corrected_text).filter(
            OcrCorrection.predicted_text.isnot(None),
            OcrCorrection.corrected_text.isnot(None),
        ).limit(5000).all()
        pairs = [(r[0], r[1]) for r in rows if r[0] and r[1]]
        return {"top_confusions": compute_char_confusions(pairs, top_k=top_k)}
    except Exception:
        return {"top_confusions": []}

# Redirection documentation
@app.get("/api/v1/docs", include_in_schema=False)
async def redirect_v1_docs():
    return RedirectResponse(url="/docs")

# Interface Angular statique
frontend_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "front-angular", "dist", "front-angular", "browser"
)
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def root():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": f"Bienvenue sur l'API {settings.PROJECT_NAME}",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "database": "PostgreSQL"
    }
