"""
Routes API — Jobs OCR asynchrones (ARCH-2 / §2.3, §5.4).
POST /api/v1/ocr/jobs      → 202 Accepted { job_id, status: "pending" }
GET  /api/v1/ocr/jobs/{id} → { id, status, progress, result, error_message }
"""
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.ocr_job import OcrJob
from app.db.models.course import NotebookPage, Lesson, Subject
from app.schemas.ocr_jobs import (
    OcrJobCreateRequest,
    JobCreatedResponse,
    OcrJobStatusResponse,
)
from app.core.security import extract_user_id_from_header
from app.workers.ocr_worker import dispatch_ocr_job

logger = logging.getLogger("ocr_jobs_api")
router = APIRouter()


def _require_user_id(authorization: Optional[str]) -> str:
    user_id = extract_user_id_from_header(authorization)
    if not user_id or user_id == "usr-guest":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise pour soumettre un job OCR.",
        )
    return user_id


@router.post(
    "/ocr/jobs",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["OCR Jobs"],
)
async def create_ocr_job(
    request: OcrJobCreateRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Crée un job OCR asynchrone pour traiter une page ou un ensemble de tracés.
    Retourne immédiatement HTTP 202 Accepted avec l'identifiant du job.
    Effectue un contrôle d'accès anti-IDOR si une page_id est fournie.
    """
    user_id = _require_user_id(authorization)
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Identifiant utilisateur invalide.")

    # Contrôle anti-IDOR si page_id est fournie
    if request.page_id:
        try:
            page_uuid = uuid.UUID(request.page_id)
            page = (
                db.query(NotebookPage)
                .join(Lesson, NotebookPage.lesson_id == Lesson.id)
                .join(Subject, Lesson.subject_id == Subject.id)
                .filter(NotebookPage.id == page_uuid, Subject.user_id == user_uuid)
                .first()
            )
            if not page:
                raise HTTPException(status_code=404, detail="Page introuvable ou accès refusé.")
        except ValueError:
            raise HTTPException(status_code=400, detail="page_id invalide.")

    # Création du job
    job = OcrJob(
        user_id=user_uuid,
        status="pending",
        progress=0.0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Préparation du payload sérialisable
    strokes_dump = [
        s.model_dump() if hasattr(s, "model_dump") else s
        for s in request.strokes
    ]
    opts_dump = (
        request.options.model_dump()
        if hasattr(request.options, "model_dump")
        else (request.options or {})
    )

    payload = {
        "strokes": strokes_dump,
        "canvasWidth": request.canvasWidth,
        "canvasHeight": request.canvasHeight,
        "options": opts_dump,
        "user_id": user_id,
    }

    # Dispatch Celery si disponible avec repli transparent sur BackgroundTasks (ARCH-2)
    dispatch_mode = dispatch_ocr_job(str(job.id), payload, background_tasks=background_tasks)

    logger.info(f"Job OCR créé : {job.id} (mode={dispatch_mode}, user={user_id})")

    return JobCreatedResponse(
        job_id=str(job.id),
        status="pending",
        message="Tâche OCR enregistrée et en cours de traitement.",
    )


@router.get(
    "/ocr/jobs/{job_id}",
    response_model=OcrJobStatusResponse,
    tags=["OCR Jobs"],
)
async def get_ocr_job_status(
    job_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Consulte l'état d'avancement et le résultat d'un job OCR.
    Protection anti-IDOR : seul le propriétaire du job peut y accéder.
    """
    user_id = _require_user_id(authorization)
    try:
        user_uuid = uuid.UUID(user_id)
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Identifiant de job invalide.")

    job = db.query(OcrJob).filter(OcrJob.id == job_uuid).first()
    if not job or job.user_id != user_uuid:
        raise HTTPException(status_code=404, detail="Job OCR introuvable ou accès refusé.")

    return OcrJobStatusResponse(
        id=str(job.id),
        status=job.status,
        progress=round(job.progress, 2),
        error_message=job.error_message,
        result=job.result_json,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )
