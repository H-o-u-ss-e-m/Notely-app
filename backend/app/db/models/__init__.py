"""Import de tous les modeles pour qu'Alembic et create_all les detectent."""
from app.db.base import Base
from app.db.models.user import User, RefreshToken
from app.db.models.course import Subject, Lesson, NotebookPage, Stroke
from app.db.models.ocr_correction import OcrCorrection
from app.db.models.user_settings import UserSettings
from app.db.models.user_dictionary import UserDictionary
from app.db.models.ocr_job import OcrJob
from app.db.models.model_version import ModelVersion
from app.db.models.audit_log import AuditLog

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "Subject",
    "Lesson",
    "NotebookPage",
    "Stroke",
    "OcrCorrection",
    "UserSettings",
    "UserDictionary",
    "OcrJob",
    "ModelVersion",
    "AuditLog",
]
