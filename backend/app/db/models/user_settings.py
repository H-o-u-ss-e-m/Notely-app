import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class UserSettings(Base):
    """
    Paramètres utilisateur & consentements RGPD (DB-4 / SEC-8 / §5.4).
    Le serveur fait foi sur les consentements.
    """
    __tablename__ = "user_settings"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    consent_train = Column(Boolean, nullable=False, default=False)
    consent_cloud_ocr = Column(Boolean, nullable=False, default=False)
    consent_withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    ocr_language = Column(String(10), nullable=False, default="fr")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
