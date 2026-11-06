"""Dépendances FastAPI partagées (authentification et anti-IDOR — SEC-4)."""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import decode_access_token
from app.db.session import get_db
from app.db.models.course import Subject, Lesson, NotebookPage


def current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Retourne le user_id du JWT d'accès, sinon 401. Jamais de repli 'invité'."""
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization[7:].strip())
        if payload and payload.get("sub"):
            return str(payload["sub"])
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_owned_subject(
    subject_id: str,
    uid: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> Subject:
    """Récupère une matière appartenant à `uid` ou lève 404 (anti-IDOR SEC-4)."""
    try:
        subj = (
            db.query(Subject)
            .filter(Subject.id == subject_id, Subject.user_id == uid)
            .first()
        )
    except Exception:
        subj = None
    if not subj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matière introuvable")
    return subj


def get_owned_lesson(
    lesson_id: str,
    uid: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> Lesson:
    """Récupère un cours appartenant à `uid` ou lève 404 (anti-IDOR SEC-4)."""
    try:
        lesson = (
            db.query(Lesson)
            .join(Subject, Lesson.subject_id == Subject.id)
            .filter(Lesson.id == lesson_id, Subject.user_id == uid)
            .first()
        )
    except Exception:
        lesson = None
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cours introuvable")
    return lesson


def get_owned_page(
    page_id: str,
    uid: str = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> NotebookPage:
    """Récupère une page appartenant à `uid` ou lève 404 (anti-IDOR SEC-4)."""
    try:
        page = (
            db.query(NotebookPage)
            .join(Lesson, NotebookPage.lesson_id == Lesson.id)
            .join(Subject, Lesson.subject_id == Subject.id)
            .filter(NotebookPage.id == page_id, Subject.user_id == uid)
            .first()
        )
    except Exception:
        page = None
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page introuvable")
    return page
