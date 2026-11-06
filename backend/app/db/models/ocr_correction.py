"""
Modèle SQLAlchemy — Corrections OCR utilisateur.

Chaque entrée représente une correction validée par l'utilisateur :
  - texte original reconnu par le modèle
  - texte corrigé par l'utilisateur

Ces corrections peuvent alimenter un futur fine-tuning avec consentement explicite.
La table stocke aussi les tracés originaux (strokes_json) pour permettre de régénérer
les images d'entraînement avec les mêmes paramètres de rendu que la production.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Float, Text, Index, Integer, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.db.base import Base


class OcrCorrection(Base):
    """
    Table des corrections OCR validées par l'utilisateur.

    consent_train = True  : l'utilisateur autorise l'usage pour améliorer le modèle.
    strokes_json          : copie des tracés au moment de la correction (pour dataset).
    predicted_text        : ce que le modèle a reconnu initialement.
    corrected_text        : ce que l'utilisateur a corrigé.
    """
    __tablename__ = "ocr_corrections"
    __table_args__ = (
        Index("ix_corrections_user_lang", "user_id", "language", text("created_at DESC")),
        Index("ix_corrections_train", "language",
              postgresql_where=text("consent_train AND is_validated")),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Utilisateur propriétaire (suppression en cascade si l'utilisateur est supprimé)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Contexte du document (optionnel — NULL si hors page)
    page_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notebook_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Portée (ligne ou mot) & index
    scope = Column(String(20), nullable=False, default="line")  # line | word
    word_index = Column(Integer, nullable=True)

    # Tracés concernés
    stroke_ids = Column(ARRAY(Text), nullable=False, default=list)
    strokes_json = Column(JSONB, nullable=True)          # Copie complète des tracés de la ligne
    stroke_fingerprint = Column(String(64), nullable=True, index=True)

    # Informations du moteur OCR utilisé
    engine = Column(String(100), nullable=False, default="trocr-base-handwritten")
    model_version = Column(String(50), nullable=True)    # Version future du modèle
    language = Column(String(10), nullable=False, default="fr")   # fr | en | ar | de

    # Textes
    predicted_text = Column(Text, nullable=False)        # Texte reconnu par le modèle
    corrected_text = Column(Text, nullable=False)        # Texte corrigé par l'utilisateur
    line_predicted = Column(Text, nullable=True)
    line_corrected = Column(Text, nullable=True)
    alternatives = Column(JSONB, nullable=True)
    confidence = Column(Float, nullable=True)            # Score de confiance original
    source = Column(String(20), nullable=False, default="manual")  # manual | suggestion | dictionary

    # Consentement explicite (opt-in — False par défaut)
    consent_train = Column(Boolean, nullable=False, default=False)
    consent_withdrawn_at = Column(DateTime(timezone=True), nullable=True)

    # État de validation
    is_validated = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relations
    user = relationship("User")

    def __repr__(self):
        return (
            f"<OcrCorrection user={self.user_id} "
            f"'{self.predicted_text[:20]}' → '{self.corrected_text[:20]}'>"
        )
