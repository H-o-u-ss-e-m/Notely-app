"""
firebase.py — MODULE DÉSACTIVÉ
Firebase/Firestore a été remplacé par PostgreSQL (SQLAlchemy).
Ce fichier est conservé pour éviter les erreurs d'import dans d'anciens modules
qui pourraient encore y faire référence. Supprimez les imports après nettoyage complet.
"""
import logging

logger = logging.getLogger(__name__)

db = None  # Ancienne référence Firestore — toujours None (PostgreSQL utilisé à la place)


def init_firebase():
    """Fonction conservée pour compatibilité — NE FAIT RIEN. Utiliser PostgreSQL."""
    logger.info("Firebase désactivé — PostgreSQL est la source de vérité unique.")
    return None
