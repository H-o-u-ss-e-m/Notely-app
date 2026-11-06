"""
Worker asynchrone pour les tâches OCR (ARCH-2 / §2.3, §5.4).
Expose `dispatch_ocr_job` qui délègue à Celery si actif ou replie sur BackgroundTasks.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import BackgroundTasks

from app.workers.ocr_tasks import run_ocr_pipeline_core, ocr_task

logger = logging.getLogger("ocr_worker")


def execute_ocr_job(job_id_str: str, payload: Dict[str, Any]) -> None:
    """Wrapper rétrocompatible pour exécution directe."""
    run_ocr_pipeline_core(job_id_str, payload)


def dispatch_ocr_job(
    job_id_str: str,
    payload: Dict[str, Any],
    background_tasks: Optional[BackgroundTasks] = None,
) -> str:
    """
    Délègue l'exécution à Celery (`ocr.run.delay`).
    En cas d'échec de connexion au broker (ex: Redis non actif en local/dev),
    bascule automatiquement sur `BackgroundTasks` pour assurer la continuité.
    """
    try:
        # Essai de dispatch Celery si le worker et le broker sont configurés
        if ocr_task is not None:
            res = ocr_task.delay(job_id_str, payload)
            logger.info(f"Job {job_id_str} expédié à Celery (task_id={res.id})")
            return "celery"
        raise RuntimeError("Celery non disponible dans l'environnement")
    except Exception as e:
        logger.warning(
            f"Broker Celery injoignable ({e}). Bascule automatique sur BackgroundTasks pour le job {job_id_str}."
        )
        if background_tasks:
            background_tasks.add_task(run_ocr_pipeline_core, job_id_str, payload)
            return "background_task"
        else:
            # Exécution en tâche de fond immédiate si pas de background_tasks
            import threading
            t = threading.Thread(target=run_ocr_pipeline_core, args=(job_id_str, payload), daemon=True)
            t.start()
            return "thread"
