"""
Modèles SQLAlchemy — Utilisateurs et Sessions/RefreshTokens.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    """Table des comptes utilisateurs."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="student")  # 'student' | 'teacher'
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    subjects = relationship("Subject", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class RefreshToken(Base):
    """Table des refresh tokens (sessions renouvelables avec rotation par famille — SEC-3)."""
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = Column(UUID(as_uuid=True), nullable=False, index=True, default=uuid.uuid4)
    token_hash = Column(String(255), nullable=False, unique=True)  # Hash SHA256 du token opaque
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relations
    user = relationship("User", back_populates="refresh_tokens")

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None and self.used_at is None and self.expires_at > datetime.utcnow()

    def __repr__(self):
        return f"<RefreshToken user_id={self.user_id} family_id={self.family_id}>"
