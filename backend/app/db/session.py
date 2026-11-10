"""
Session SQLAlchemy — Connexion PostgreSQL.
Fournit la session de base de données utilisée dans toute l'application.
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

logger = logging.getLogger(__name__)

# URL de connexion depuis l'environnement
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

engine_kwargs = {"echo": False}
if "sqlite" in DATABASE_URL:
    from sqlalchemy.pool import StaticPool
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool
else:
    connect_args = {}
    if "postgresql" in DATABASE_URL:
        connect_args["connect_timeout"] = 2
    engine_kwargs["connect_args"] = connect_args
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dépendance FastAPI : crée une session DB par requête HTTP,
    la ferme proprement à la fin (commit ou rollback automatique).
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    """Vérifie que PostgreSQL est accessible."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("PostgreSQL inaccessible : %s", e)
        return False
