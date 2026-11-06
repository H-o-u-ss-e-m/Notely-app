"""
Schémas Pydantic pour le feedback OCR, le dictionnaire personnel et les paramètres RGPD.
(ML-5, DB-4, SEC-8 / §8.5, §8.6, §5.4).
"""
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class OcrFeedbackRequest(BaseModel):
    """Corps de la requête POST /api/v1/ocr/feedback."""
    stroke_ids: List[str] = Field(default_factory=list, description="IDs des tracés de la ligne corrigée")
    strokes: Optional[List[Any]] = Field(None, description="Tracés complets (pour dataset futur)")
    page_id: Optional[str] = Field(None, description="UUID de la page notebook (si connu)")
    predicted_text: str = Field(..., description="Texte reconnu par le modèle")
    corrected_text: str = Field(..., description="Texte corrigé par l'utilisateur")
    scope: str = Field("line", description="Étendue : 'line' ou 'word'")
    word_index: Optional[int] = Field(None, description="Index du mot si scope='word'")
    stroke_fingerprint: Optional[str] = Field(None, description="Empreinte SHA256 des tracés pour mémoire exacte")
    line_predicted: Optional[str] = Field(None, description="Ligne prédite complète")
    line_corrected: Optional[str] = Field(None, description="Ligne corrigée complète")
    alternatives: Optional[List[str]] = Field(None, description="Alternatives n-best")
    confidence: Optional[float] = Field(None, description="Score de confiance du modèle")
    engine: str = Field("trocr-base-handwritten", description="Moteur OCR utilisé")
    language: str = Field("fr", description="Langue OCR (fr|en|ar|de)")
    consent_train: bool = Field(
        False,
        description="Consentement explicite pour utilisation en entraînement (opt-in)",
    )
    source: str = Field("manual", description="Origine de la correction : 'manual' | 'suggestion' | 'dictionary'")


class OcrFeedbackResponse(BaseModel):
    """Réponse de la route POST /api/v1/ocr/feedback."""
    success: bool = True
    correction_id: str
    message: str = "Correction enregistrée."


class OcrCorrectionItem(BaseModel):
    """Élément de la liste des corrections d'un utilisateur."""
    id: str
    predicted_text: str
    corrected_text: str
    scope: str = "line"
    word_index: Optional[int] = None
    language: str
    engine: str
    confidence: Optional[float]
    consent_train: bool
    source: str = "manual"
    created_at: str

    class Config:
        from_attributes = True


class OcrCorrectionsListResponse(BaseModel):
    """Réponse de GET /api/v1/ocr/corrections."""
    corrections: List[OcrCorrectionItem]
    total: int


class UserDictionaryItem(BaseModel):
    """Élément d'une substitution enregistrée dans le dictionnaire personnel."""
    id: str
    language: str
    wrong: str
    right: str
    count: int
    last_seen: str

    class Config:
        from_attributes = True


class UserDictionaryListResponse(BaseModel):
    """Réponse de GET /api/v1/me/dictionary ou GET /api/v1/ocr/dictionary."""
    items: List[UserDictionaryItem]
    total: int


class UserSettingsResponse(BaseModel):
    """Paramètres utilisateur & consentements RGPD."""
    user_id: str
    consent_train: bool
    consent_cloud_ocr: bool
    consent_withdrawn_at: Optional[str] = None
    ocr_language: str
    updated_at: str

    class Config:
        from_attributes = True


class UserSettingsUpdateRequest(BaseModel):
    """Mise à jour des consentements et préférences."""
    consent_train: Optional[bool] = None
    consent_cloud_ocr: Optional[bool] = None
    ocr_language: Optional[str] = None
