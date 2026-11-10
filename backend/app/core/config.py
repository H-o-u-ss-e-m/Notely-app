import os
import json
from typing import List
from dotenv import load_dotenv

# Charger .env depuis la racine du projet
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv(os.path.join(_root, '.env'))

# Valeurs connues comme compromises (apparues dans le code / la documentation) : refusées.
_COMPROMISED_JWT_SECRETS = {
    "notely-secret-key-quantum-ink-production-secure-v1",
    "change-this-secret-key-in-production",
    "0f0b1ca76dd33216e741a7724eb00f8e3c1220b5f8f1d713a53706e0edc939a3",
}

_DEV_CORS_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


class ConfigError(RuntimeError):
    """Configuration invalide : l'application refuse de démarrer."""


def _require_env(name: str, hint: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Variable d'environnement obligatoire manquante : {name}. {hint}")
    return value


def _parse_origins(raw: str | None) -> List[str]:
    """Accepte une liste JSON (["a","b"]) ou une liste séparée par des virgules."""
    if raw is None or not raw.strip():
        return list(_DEV_CORS_ORIGINS)
    raw = raw.strip()
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"CORS_ORIGINS : JSON invalide ({exc})") from exc
        return [str(o).strip() for o in parsed if str(o).strip()]
    return [o.strip() for o in raw.split(",") if o.strip()]


def _load_jwt_secret() -> str:
    secret = _require_env(
        "JWT_SECRET_KEY",
        "Générez-en une : python -c \"import secrets; print(secrets.token_urlsafe(64))\"",
    )
    if len(secret) < 32:
        raise ConfigError("JWT_SECRET_KEY trop courte (minimum 32 caractères).")
    if secret in _COMPROMISED_JWT_SECRETS:
        raise ConfigError(
            "JWT_SECRET_KEY correspond à une valeur connue/compromise : générez un nouveau secret."
        )
    return secret


def _load_cors_origins(env: str) -> List[str]:
    origins = _parse_origins(os.getenv("CORS_ORIGINS"))
    if env == "prod":
        if "*" in origins:
            raise ConfigError("CORS '*' interdit en production.")
        if not all(o.startswith("https://") for o in origins):
            raise ConfigError("Les origines CORS de production doivent être en https.")
    elif "*" in origins:
        # allow_credentials=True est incompatible avec '*' : on refuse même en dev.
        raise ConfigError("CORS_ORIGINS ne doit pas contenir '*' (listez les origines explicitement).")
    return origins


class Settings:
    PROJECT_NAME: str = "Notely — Smart Handwriting Notebook API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"

    ENV: str = os.getenv("ENV", "dev").lower()
    if ENV not in ("dev", "staging", "prod", "test", "ci"):
        raise ConfigError("ENV doit valoir dev, staging, prod, test ou ci.")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Base de données PostgreSQL — repli SQLite mémoire pour mode test/ci
    DATABASE_URL: str = (
        os.getenv("DATABASE_URL", "sqlite:///:memory:")
        if ENV in ("test", "ci")
        else _require_env(
            "DATABASE_URL",
            "Exemple : postgresql+psycopg2://user:password@localhost:5432/notely",
        )
    )

    # JWT — AUCUNE valeur par défaut
    JWT_SECRET_KEY: str = _load_jwt_secret()
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    if JWT_ALGORITHM not in ("HS256",):
        raise ConfigError("JWT_ALGORITHM non supporté (HS256 uniquement).")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # TrOCR
    TROCR_MODEL: str = os.getenv("TROCR_MODEL", "microsoft/trocr-base-handwritten")
    DEVICE_SETTING: str = os.getenv("DEVICE", "auto")

    # Stockage des fichiers PDF générés
    STORAGE_ROOT: str = os.getenv("STORAGE_ROOT", "storage")

    # Paramètres segmentation
    MIN_STROKE_POINTS: int = 2
    PADDING_FACTOR: float = 0.35
    DESKEW_THRESHOLD_DEG: float = 2.0
    MAX_DESKEW_DEG: float = 15.0

    # Limites de requête (anti-DoS)
    MAX_REQUEST_BODY_MB: int = int(os.getenv("MAX_REQUEST_BODY_MB", "25"))

    # Optimisations ML (ML-12b)
    QUANTIZE_INT8_CPU: bool = os.getenv("QUANTIZE_INT8_CPU", "true").lower() == "true"
    MIN_CLIENT_VERSION: str = os.getenv("MIN_CLIENT_VERSION", "1.0.0")

    # CORS — source unique de vérité (liste explicite, jamais '*')
    CORS_ORIGINS: List[str] = _load_cors_origins(ENV)


settings = Settings()
