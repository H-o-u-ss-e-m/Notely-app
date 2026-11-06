import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class ModelVersion(Base):
    """
    Registre des versions de modèle déployées (ML-7 / §5.4, §8.7).
    Stocke le statut (candidate, active, retired) et les métriques associées.
    """
    __tablename__ = "model_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(64), nullable=False)
    version = Column(String(32), nullable=False)
    status = Column(String(20), nullable=False, default="candidate")  # candidate | active | retired
    metrics = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
