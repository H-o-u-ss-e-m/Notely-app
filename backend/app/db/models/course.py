"""
Modèles SQLAlchemy — Matières (Subjects), Cours (Lessons), Pages et Tracés (DB-3).
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime,
    ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class Subject(Base):
    """Table des matières / espaces de travail."""
    __tablename__ = "subjects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    color = Column(String(20), nullable=False, default="#1E40AF")
    description = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = relationship("User", back_populates="subjects")
    lessons = relationship("Lesson", back_populates="subject", cascade="all, delete-orphan", order_by="Lesson.created_at.desc()")

    def __repr__(self):
        return f"<Subject {self.name}>"


class Lesson(Base):
    """Table des cours."""
    __tablename__ = "lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Corbeille 30 jours (DB-3)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    subject = relationship("Subject", back_populates="lessons")
    pages = relationship(
        "NotebookPage",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="NotebookPage.page_number"
    )

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def __repr__(self):
        return f"<Lesson {self.title}>"


class NotebookPage(Base):
    """Table des pages d'un cours."""
    __tablename__ = "notebook_pages"
    __table_args__ = (
        UniqueConstraint("lesson_id", "page_number", name="uq_lesson_page_number"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False, default=1)
    width = Column(Float, nullable=False, default=794.0)
    height = Column(Float, nullable=False, default=1123.0)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    lesson = relationship("Lesson", back_populates="pages")
    strokes = relationship(
        "Stroke",
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="Stroke.seq, Stroke.start_time"
    )

    def __repr__(self):
        return f"<NotebookPage lesson_id={self.lesson_id} page={self.page_number}>"


class Stroke(Base):
    """
    Table des tracés manuscrits (DB-3).
    Clé primaire interne UUID `id` + `client_id` unique par page (`uq_strokes_page_client`).
    """
    __tablename__ = "strokes"
    __table_args__ = (
        UniqueConstraint("page_id", "client_id", name="uq_strokes_page_client"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("notebook_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(String(255), nullable=False)
    seq = Column(Integer, nullable=False, default=0)
    tool = Column(String(50), nullable=False, default="pen")         # 'pen' | 'diagram' | 'eraser'
    content_type = Column(String(50), nullable=False, default="normal")  # 'normal' | 'h1'..'h6'
    color = Column(String(20), nullable=False, default="#000000")
    width = Column(Float, nullable=False, default=3.0)
    points = Column(JSONB, nullable=False, default=list)             # [{x, y, timestamp, pressure}]
    bbox = Column(JSONB, nullable=True)                              # {xMin, yMin, xMax, yMax}
    start_time = Column(Float, nullable=False, default=0.0)
    end_time = Column(Float, nullable=False, default=0.0)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relations
    page = relationship("NotebookPage", back_populates="strokes")

    def __repr__(self):
        return f"<Stroke id={self.id} client_id={self.client_id} tool={self.tool}>"
