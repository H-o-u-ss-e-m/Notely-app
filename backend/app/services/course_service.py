"""
LEGACY — course_service.py
Ce service est remplacé par app.modules.courses.service (PostgreSQL).
Ce fichier est conservé pour éviter les erreurs d'import de modules qui y font encore référence.
NE PAS UTILISER — utilisez app.modules.courses.service.course_service
"""
from app.modules.courses.service import course_service  # noqa: F401
