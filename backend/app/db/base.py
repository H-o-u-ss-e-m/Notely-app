"""
Base SQLAlchemy — Classe de base partagée par tous les modèles ORM.
"""
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime, func


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy."""
    pass
