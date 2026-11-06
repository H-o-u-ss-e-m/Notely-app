"""
Endpoints d'administration MLOps et registre de modèles (ML-7 / §8.7).
- Consultation des versions enregistrées.
- Promotion candidate -> canary -> active avec validation humaine.
- Rollback immédiat en une commande.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.db.session import get_db
from app.api.deps import current_user_id
from app.db.models.model_version import ModelVersion
from training.promote import ModelRegistryService

router = APIRouter(prefix="/ocr/models", tags=["MLOps - Modèles"])


class ModelVersionOut(BaseModel):
    id: str
    name: str
    version: str
    status: str
    metrics: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    activated_at: Optional[str] = None


class PromoteRequest(BaseModel):
    model_version_id: str
    human_approved: bool = Field(..., description="Validation humaine obligatoire (§8.7)")


class RollbackRequest(BaseModel):
    model_name: str = Field(default="trocr_fr")


@router.get("", response_model=List[ModelVersionOut])
def list_models(db: Session = Depends(get_db), _user=Depends(current_user_id)):
    """Liste l'ensemble des modèles et versions du registre."""
    rows = db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()
    return [
        ModelVersionOut(
            id=str(r.id),
            name=r.name,
            version=r.version,
            status=r.status,
            metrics=r.metrics,
            created_at=r.created_at.isoformat() if r.created_at else None,
            activated_at=r.activated_at.isoformat() if r.activated_at else None,
        )
        for r in rows
    ]


@router.post("/promote/canary")
def promote_to_canary(
    req: PromoteRequest,
    db: Session = Depends(get_db),
    _user=Depends(current_user_id),
):
    """Promeut un modèle candidat vers le statut 'canary' (10% de trafic)."""
    try:
        import uuid
        res = ModelRegistryService.promote_candidate_to_canary(
            db=db,
            model_version_id=uuid.UUID(req.model_version_id),
            human_approved=req.human_approved,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/promote/active")
def promote_to_active(
    model_name: str = "trocr_fr",
    db: Session = Depends(get_db),
    _user=Depends(current_user_id),
):
    """Bascule le modèle canary validé en statut 'active'."""
    try:
        return ModelRegistryService.promote_canary_to_active(db, model_name=model_name)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/rollback")
def rollback_model(
    req: RollbackRequest,
    db: Session = Depends(get_db),
    _user=Depends(current_user_id),
):
    """Rollback immédiat vers la version précédente du modèle."""
    try:
        return ModelRegistryService.rollback_active(db, model_name=req.model_name)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
