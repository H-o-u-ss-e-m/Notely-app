"""
Gestion du dictionnaire personnel de l'utilisateur (DB-4 / ML-5 / §8.5.b).
Maintient les corrections récurrentes par utilisateur et par langue.
"""
import uuid
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models.user_dictionary import UserDictionary


def bump_user_dictionary(
    db: Session,
    user_id: uuid.UUID,
    language: str,
    wrong: str,
    right: str,
) -> Optional[UserDictionary]:
    """
    Incrémente le compteur d'une substitution ou crée une nouvelle entrée.
    Exclut les chaînes vides, identiques ou trop longues (> 100 caracs).
    """
    w = wrong.strip().lower()
    r = right.strip()
    if not w or not r or w == r.lower() or len(w) > 100 or len(r) > 100 or " " in w:
        return None

    entry = (
        db.query(UserDictionary)
        .filter(
            UserDictionary.user_id == user_id,
            UserDictionary.language == language,
            UserDictionary.wrong == w,
        )
        .first()
    )

    if entry:
        entry.right = r
        entry.count += 1
        entry.last_seen = datetime.utcnow()
    else:
        entry = UserDictionary(
            user_id=user_id,
            language=language,
            wrong=w,
            right=r,
            count=1,
            last_seen=datetime.utcnow(),
        )
        db.add(entry)

    db.commit()
    db.refresh(entry)
    return entry


def get_user_dictionary_map(
    db: Session,
    user_id: uuid.UUID,
    language: str = "fr",
) -> Dict[str, Tuple[str, int]]:
    """
    Charge le dictionnaire personnel sous la forme :
    { "wrong_lower": ("RightText", count) }
    """
    entries = (
        db.query(UserDictionary)
        .filter(
            UserDictionary.user_id == user_id,
            UserDictionary.language == language,
        )
        .order_by(UserDictionary.count.desc())
        .limit(2000)
        .all()
    )
    return {e.wrong.lower(): (e.right, e.count) for e in entries}
