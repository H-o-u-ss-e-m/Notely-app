"""
Tâche Celery pour l'inférence OCR asynchrone (ARCH-2 / §2.3, §5.4).
Exécute le pipeline HTR avec suivi de progression, soft_time_limit et gestion d'erreurs.
"""
import uuid
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from app.workers.celery_app import celery_app, HAS_CELERY
from app.db.session import SessionLocal
from app.db.models.ocr_job import OcrJob
from app.schemas.strokes import Stroke
from app.schemas.recognition import RecognitionOptions
from app.services.handwriting_service import handwriting_service

logger = logging.getLogger("ocr_tasks")


def run_ocr_pipeline_core(
    job_id_str: str,
    payload: Dict[str, Any],
    on_progress: Optional[Callable[[float], None]] = None,
) -> Dict[str, Any]:
    """
    Cœur de traitement HTR partagé entre Celery worker et BackgroundTasks.
    """
    job_uuid = uuid.UUID(job_id_str)
    with SessionLocal() as db:
        job = db.query(OcrJob).filter(OcrJob.id == job_uuid).first()
        if not job:
            raise ValueError(f"Job {job_id_str} introuvable.")

        job.status = "processing"
        job.progress = 0.1
        db.commit()

        if on_progress:
            on_progress(0.1)

        try:
            raw_strokes = payload.get("strokes", [])
            strokes = [
                Stroke(**s) if isinstance(s, dict) else s
                for s in raw_strokes
            ]
            canvas_w = float(payload.get("canvasWidth", 800.0))
            canvas_h = float(payload.get("canvasHeight", 1000.0))
            raw_opts = payload.get("options") or {}
            options = RecognitionOptions(**raw_opts) if isinstance(raw_opts, dict) else raw_opts
            user_id = payload.get("user_id", "anon")

            job.progress = 0.4
            db.commit()
            if on_progress:
                on_progress(0.4)

            # Inférence
            result = handwriting_service.process_strokes(
                strokes=strokes,
                canvas_w=canvas_w,
                canvas_h=canvas_h,
                options=options,
                user_id=str(user_id),
            )

            job.status = "completed"
            job.progress = 1.0
            job.result_json = result.model_dump()
            job.updated_at = datetime.utcnow()
            db.commit()

            if on_progress:
                on_progress(1.0)

            logger.info(f"Job {job_id_str} terminé ({len(result.lines)} lignes).")
            return job.result_json

        except Exception as e:
            logger.exception(f"Échec du job {job_id_str} : {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()
            db.commit()
            raise


if HAS_CELERY and celery_app:
    @celery_app.task(
        bind=True,
        name="ocr.run",
        soft_time_limit=120,
        time_limit=150,
        max_retries=1,
    )
    def ocr_task(self, job_id: str, payload: Dict[str, Any]):
        """
        Tâche Celery officielle 'ocr.run' avec soft_time_limit 120s et tracking d'état.
        """
        def _update_progress(p: float):
            self.update_state(state="PROGRESS", meta={"progress": p, "job_id": job_id})

        return run_ocr_pipeline_core(job_id, payload, on_progress=_update_progress)
else:
    ocr_task = None
