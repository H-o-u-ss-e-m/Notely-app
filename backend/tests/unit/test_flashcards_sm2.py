"""Tests Chantier 9 — SM-2, génération de cartes et API flashcards (SQLite mémoire + anti-IDOR)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.models.course import Lesson, Subject
from app.db.models.flashcard import Flashcard
from app.db.models.user import User
from app.db.session import get_db
from app.domain.sm2 import CardState, generate_cards_from_elements, sm2_update
from app.main import app


# ── SM-2 pur ──────────────────────────────────────────────────────────────────

def test_sm2_first_second_third_intervals():
    s = CardState()
    s = sm2_update(s, 4)
    assert (s.repetitions, s.interval_days) == (1, 1)
    s = sm2_update(s, 4)
    assert (s.repetitions, s.interval_days) == (2, 6)
    s = sm2_update(s, 4)
    assert s.repetitions == 3
    assert s.interval_days == round(6 * 2.5)  # facteur 4 : inchangé (2.5)


def test_sm2_failure_resets_but_keeps_ease():
    s = sm2_update(sm2_update(CardState(), 5), 5)
    ease = s.ease_factor
    failed = sm2_update(s, 2)
    assert failed.repetitions == 0 and failed.interval_days == 1
    assert failed.ease_factor == ease


def test_sm2_ease_increases_on_5_and_never_below_1_3():
    assert sm2_update(CardState(), 5).ease_factor == pytest.approx(2.6)
    s = CardState(ease_factor=1.31, interval_days=6, repetitions=2)
    for _ in range(10):
        s = sm2_update(s, 3)
    assert s.ease_factor >= 1.3


def test_sm2_rejects_invalid_quality():
    with pytest.raises(ValueError):
        sm2_update(CardState(), 6)
    with pytest.raises(ValueError):
        sm2_update(CardState(), -1)


def test_generate_cards_from_elements():
    els = [
        {"type": "h1", "text": "Photosynthèse"},
        {"type": "paragraph", "text": "Conversion de la lumière"},
        {"type": "paragraph", "text": "en énergie chimique."},
        {"type": "diagram", "text": ""},
        {"type": "h2", "text": "Titre vide"},
        {"type": "h2", "text": "Chlorophylle"},
        {"type": "paragraph", "text": "Pigment vert."},
    ]
    cards = generate_cards_from_elements(els)
    assert cards == [
        ("Photosynthèse", "Conversion de la lumière en énergie chimique."),
        ("Chlorophylle", "Pigment vert."),
    ]


# ── API ───────────────────────────────────────────────────────────────────────

@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for model in (User, Subject, Lesson, Flashcard):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    db = Session()
    users = []
    for i in range(2):
        u = User(email=f"u{i}@notely.app", password_hash="x")
        db.add(u)
        users.append(u)
    db.commit()
    yield TestClient(app), db, [str(u.id) for u in users]
    app.dependency_overrides.pop(get_db, None)
    db.close()


def _h(uid):
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


def test_requires_auth(env):
    client, _, _ = env
    assert client.get("/api/v1/flashcards/due").status_code == 401


def test_create_review_and_due_flow(env):
    client, db, (a, _) = env
    r = client.post("/api/v1/flashcards", json={"front": "Q", "back": "R"}, headers=_h(a))
    assert r.status_code == 201
    card_id = r.json()["id"]

    due = client.get("/api/v1/flashcards/due", headers=_h(a)).json()
    assert [c["id"] for c in due] == [card_id]

    rv = client.post(f"/api/v1/flashcards/{card_id}/review", json={"quality": 5}, headers=_h(a))
    assert rv.status_code == 200
    body = rv.json()
    assert body["repetitions"] == 1 and body["interval_days"] == 1
    assert client.get("/api/v1/flashcards/due", headers=_h(a)).json() == []

    assert client.post(f"/api/v1/flashcards/{card_id}/review", json={"quality": 9}, headers=_h(a)).status_code == 422


def test_from_ocr_creates_cards(env):
    client, _, (a, _) = env
    r = client.post(
        "/api/v1/flashcards/from-ocr",
        json={"elements": [{"type": "h1", "text": "Titre"}, {"type": "paragraph", "text": "Contenu"}]},
        headers=_h(a),
    )
    assert r.status_code == 201
    assert [(c["front"], c["back"]) for c in r.json()] == [("Titre", "Contenu")]


def test_idor_other_user_gets_404(env):
    client, db, (a, b) = env
    card_id = client.post("/api/v1/flashcards", json={"front": "Q", "back": "R"}, headers=_h(a)).json()["id"]
    assert client.post(f"/api/v1/flashcards/{card_id}/review", json={"quality": 4}, headers=_h(b)).status_code == 404
    assert client.delete(f"/api/v1/flashcards/{card_id}", headers=_h(b)).status_code == 404
    assert client.get("/api/v1/flashcards", headers=_h(b)).json() == []
    # lesson d'un autre utilisateur
    subj = Subject(user_id=uuid.UUID(a), name="M")
    db.add(subj); db.commit()
    les = Lesson(subject_id=subj.id, title="L")
    db.add(les); db.commit()
    r = client.post("/api/v1/flashcards", json={"front": "Q", "back": "R", "lesson_id": str(les.id)}, headers=_h(b))
    assert r.status_code == 404
    assert client.delete(f"/api/v1/flashcards/{card_id}", headers=_h(a)).status_code == 204
