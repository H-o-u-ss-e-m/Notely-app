import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class UserDictionary(Base):
    """
    Dictionnaire personnel de l'utilisateur (DB-4 / ML-5 / §5.4, §8.5.b).
    Enregistre les corrections fréquentes pour les réappliquer automatiquement.
    """
    __tablename__ = "user_dictionaries"
    __table_args__ = (
        UniqueConstraint("user_id", "language", "wrong", name="uq_userdict"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language = Column(String(10), nullable=False, default="fr")
    wrong = Column(String(100), nullable=False)
    right = Column(String(100), nullable=False)
    count = Column(Integer, nullable=False, default=1)
    last_seen = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user = relationship("User")
