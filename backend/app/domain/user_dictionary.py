"""
Gestion du dictionnaire personnel de l'utilisateur (DB-4 / ML-5 / §8.5.b & Plan v2 §1.3).
Maintient les corrections par utilisateur et par langue, indexées via normalize_key.
"""
import uuid
from datetime import datetime
from typing import Dict, Tuple, Optional

from sqlalchemy.orm import Session
from app.db.models.user_dictionary import UserDictionary
from app.domain.correction_layer import normalize_key


def bump_user_dictionary(
    db: Session,
    user_id: uuid.UUID,
    language: str,
    wrong: str,
    right: str,
) -> Optional[UserDictionary]:
    """
    Incrémente le compteur d'une substitution ou crée une nouvelle entrée.
    Normalise la clé `wrong` via `normalize_key(wrong, language)` (support arabe & latin).
    """
    lang = (language or "fr").lower().strip()
    w = normalize_key(wrong, lang)
    r = (right or "").strip()
    r_norm = normalize_key(r, lang)
    if not w or not r or w == r_norm or len(w) > 100 or len(r) > 100:
        return None

    entry = (
        db.query(UserDictionary)
        .filter(
            UserDictionary.user_id == user_id,
            UserDictionary.language == lang,
            UserDictionary.wrong == w,
        )
        .first()
    )

    if entry:
        entry.right = r
        entry.count = (entry.count or 1) + 1
        entry.last_seen = datetime.utcnow()
    else:
        entry = UserDictionary(
            user_id=user_id,
            language=lang,
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
    { "wrong_normalized": ("RightText", count) }
    """
    lang = (language or "fr").lower().strip()
    entries = (
        db.query(UserDictionary)
        .filter(
            UserDictionary.user_id == user_id,
            UserDictionary.language == lang,
        )
        .order_by(UserDictionary.count.desc())
        .limit(2000)
        .all()
    )
    return {normalize_key(e.wrong, lang): (e.right, e.count) for e in entries}


def load_user_subs_for_id(user_id: str, lang: str = "fr") -> Dict[str, Tuple[str, int]]:
    """Charge la carte du dictionnaire personnel pour un user_id (chaîne UUID)."""
    if not user_id or user_id in ("anon", "usr-guest"):
        return {}
    try:
        u_uuid = uuid.UUID(str(user_id))
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            return get_user_dictionary_map(db, u_uuid, language=lang)
    except Exception:
        return {}


def lookup(user_id: str, lang: str, norm_key: str) -> Optional[str]:
    """Recherche directe d'une clé normalisée dans le dictionnaire de l'utilisateur."""
    if not norm_key:
        return None
    subs = load_user_subs_for_id(user_id, lang)
    k = normalize_key(norm_key, lang)
    hit = subs.get(k)
    if hit:
        return hit[0] if isinstance(hit, (tuple, list)) else str(hit)
    return None
