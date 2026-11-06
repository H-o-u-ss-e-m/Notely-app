"""Cartes de révision (flashcards) à répétition espacée SM-2."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    ease_factor = Column(Float, nullable=False, default=2.5)
    interval_days = Column(Integer, nullable=False, default=0)
    repetitions = Column(Integer, nullable=False, default=0)
    due_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
