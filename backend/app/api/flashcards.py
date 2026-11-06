"""Flashcards : création manuelle / depuis l'OCR, file de révision SM-2, notation."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import current_user_id
from app.db.models.course import Lesson, Subject
from app.db.models.flashcard import Flashcard
from app.db.session import get_db
from app.domain.sm2 import CardState, generate_cards_from_elements, next_due, sm2_update

router = APIRouter()


class FlashcardCreate(BaseModel):
    front: str = Field(min_length=1, max_length=2000)
    back: str = Field(min_length=1, max_length=4000)
    lesson_id: Optional[uuid.UUID] = None


class OcrElementIn(BaseModel):
    type: str
    text: str = ""


class FlashcardsFromOcr(BaseModel):
    lesson_id: Optional[uuid.UUID] = None
    elements: List[OcrElementIn] = Field(max_length=500)


class ReviewIn(BaseModel):
    quality: int = Field(ge=0, le=5)


class FlashcardOut(BaseModel):
    id: uuid.UUID
    lesson_id: Optional[uuid.UUID]
    front: str
    back: str
    ease_factor: float
    interval_days: int
    repetitions: int
    due_at: datetime

    model_config = {"from_attributes": True}


def _uid(user_id: str) -> uuid.UUID:
    return uuid.UUID(user_id)


def _check_lesson_owned(db: Session, uid: uuid.UUID, lesson_id: Optional[uuid.UUID]) -> None:
    """Anti-IDOR : un cours rattaché doit appartenir à l'utilisateur."""
    if lesson_id is None:
        return
    ok = (
        db.query(Lesson.id)
        .join(Subject, Subject.id == Lesson.subject_id)
        .filter(Lesson.id == lesson_id, Subject.user_id == uid)
        .first()
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Cours introuvable")


def _get_owned_card(db: Session, uid: uuid.UUID, card_id: uuid.UUID) -> Flashcard:
    card = db.query(Flashcard).filter(Flashcard.id == card_id, Flashcard.user_id == uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    return card


@router.post("/flashcards", response_model=FlashcardOut, status_code=201)
def create_flashcard(dto: FlashcardCreate, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    uid = _uid(user_id)
    _check_lesson_owned(db, uid, dto.lesson_id)
    card = Flashcard(user_id=uid, lesson_id=dto.lesson_id, front=dto.front.strip(), back=dto.back.strip())
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.post("/flashcards/from-ocr", response_model=List[FlashcardOut], status_code=201)
def create_flashcards_from_ocr(dto: FlashcardsFromOcr, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    uid = _uid(user_id)
    _check_lesson_owned(db, uid, dto.lesson_id)
    pairs = generate_cards_from_elements([e.model_dump() for e in dto.elements])
    cards = [Flashcard(user_id=uid, lesson_id=dto.lesson_id, front=f, back=b) for f, b in pairs]
    db.add_all(cards)
    db.commit()
    for c in cards:
        db.refresh(c)
    return cards


@router.get("/flashcards", response_model=List[FlashcardOut])
def list_flashcards(user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    uid = _uid(user_id)
    return db.query(Flashcard).filter(Flashcard.user_id == uid).order_by(Flashcard.due_at).limit(500).all()


@router.get("/flashcards/due", response_model=List[FlashcardOut])
def due_flashcards(limit: int = Query(20, ge=1, le=100), user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    uid = _uid(user_id)
    now = datetime.now(timezone.utc)
    return (
        db.query(Flashcard)
        .filter(Flashcard.user_id == uid, Flashcard.due_at <= now)
        .order_by(Flashcard.due_at)
        .limit(limit)
        .all()
    )


@router.post("/flashcards/{card_id}/review", response_model=FlashcardOut)
def review_flashcard(card_id: uuid.UUID, dto: ReviewIn, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    card = _get_owned_card(db, _uid(user_id), card_id)
    new = sm2_update(CardState(card.ease_factor, card.interval_days, card.repetitions), dto.quality)
    now = datetime.now(timezone.utc)
    card.ease_factor, card.interval_days, card.repetitions = new.ease_factor, new.interval_days, new.repetitions
    card.due_at = next_due(now, new.interval_days)
    card.last_reviewed_at = now
    db.commit()
    db.refresh(card)
    return card


@router.delete("/flashcards/{card_id}", status_code=204)
def delete_flashcard(card_id: uuid.UUID, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    card = _get_owned_card(db, _uid(user_id), card_id)
    db.delete(card)
    db.commit()
