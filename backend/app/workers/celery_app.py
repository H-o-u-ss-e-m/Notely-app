"""
Configuration Celery pour les tâches d'arrière-plan (ARCH-2 / §2.3, §5.4).
Broker Redis avec sérialisation JSON sécurisée et préchargement de modèles.
Gère l'absence du paquet celery en environnement local de développement.
"""
import os
import logging

logger = logging.getLogger("celery_app")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    from celery import Celery
    from celery.signals import worker_process_init
    HAS_CELERY = True

    celery_app = Celery(
        "notely_tasks",
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=["app.workers.ocr_tasks"],
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,      # Une tâche lourde par worker à la fois
        task_acks_late=True,               # Acquittement après exécution réussie
        result_expires=86400,              # Résultats expirés après 24h
    )

    @worker_process_init.connect
    def init_worker_process(**kwargs):
        """
        Préchauffe le moteur TrOCR dans chaque processus worker au démarrage
        pour éviter la latence d'initialisation sur la première requête.
        """
        logger.info("Initialisation du worker Celery — Préchauffage des modèles HTR...")
        try:
            from app.ml.registry import registry
            chain, _ = registry.chain_for("fr")
            if chain:
                registry.get(chain[0])
                logger.info(f"Modèle primaire '{chain[0]}' préchargé avec succès dans le worker.")
        except Exception as e:
            logger.warning(f"Préchargement Celery différé : {e}")

except ImportError:
    HAS_CELERY = False
    celery_app = None
    logger.info("Paquet 'celery' non installé : exécution des jobs en BackgroundTasks.")
