"""
Schémas Pydantic pour les jobs OCR asynchrones (ARCH-2 / §2.3, §5.4).
"""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from app.schemas.strokes import Stroke
from app.schemas.recognition import RecognitionOptions


class OcrJobCreateRequest(BaseModel):
    """Corps de la requête POST /api/v1/ocr/jobs."""
    strokes: List[Stroke] = Field(..., description="Liste des tracés vectoriels à reconnaître")
    canvasWidth: float = Field(800.0, description="Largeur du canvas")
    canvasHeight: float = Field(1000.0, description="Hauteur du canvas")
    options: Optional[RecognitionOptions] = Field(default_factory=RecognitionOptions)
    page_id: Optional[str] = Field(None, description="UUID optionnel de la page pour contrôle d'accès anti-IDOR")


class JobCreatedResponse(BaseModel):
    """Réponse de création d'un job (HTTP 202 Accepted)."""
    job_id: str
    status: str = "pending"
    message: str = "Tâche OCR enregistrée et en cours de traitement."


class OcrJobStatusResponse(BaseModel):
    """Réponse d'état d'un job OCR."""
    id: str
    status: str  # pending | processing | completed | failed
    progress: float  # 0.0 à 1.0
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
