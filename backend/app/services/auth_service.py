"""
LEGACY — auth_service.py
Ce service est remplacé par app.modules.auth.service (PostgreSQL).
Ce fichier est conservé pour éviter les erreurs d'import de modules qui y font encore référence.
NE PAS UTILISER — utilisez app.modules.auth.service.auth_service
"""
from app.modules.auth.service import auth_service  # noqa: F401
