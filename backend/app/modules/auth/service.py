"""
AuthService — Logique métier d'authentification avec PostgreSQL (SEC-2 / SEC-3 / SEC-6).
"""
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.db.models.user import RefreshToken
from app.modules.auth.repository import user_repository, refresh_token_repository
from app.core.security import (
    hash_password,
    verify_password,
    fake_verify,
    create_access_token,
)
from app.core.config import settings
from app.core.ratelimit import check_login_lockout, record_login_failure, reset_login_failures
from app.schemas.auth import UserCreateDTO, UserLoginDTO, TokenDTO, UserResponseDTO

logger = logging.getLogger(__name__)


def _h(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.utcnow()


def issue_refresh(
    db: Session,
    user_id,
    family_id=None,
    user_agent: Optional[str] = None,
) -> str:
    """Émet un refresh token opaque 256 bits dans la famille `family_id` (SEC-3)."""
    raw = secrets.token_urlsafe(32)
    rt = RefreshToken(
        user_id=user_id,
        family_id=family_id or uuid.uuid4(),
        token_hash=_h(raw),
        expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        used_at=None,
        revoked_at=None,
        user_agent=user_agent,
    )
    db.add(rt)
    db.flush()
    return raw


def rotate_refresh(db: Session, raw: str) -> Tuple[uuid.UUID, str]:
    """
    Rotation d'un refresh token opaque (SEC-3) :
    - Si inconnu ou expiré → ValueError("invalid_refresh")
    - Si déjà utilisé (`used_at`) ou révoqué (`revoked_at`) → REJEU DÉTECTÉ :
      révoque toute la famille (`family_id`) et lève ValueError("refresh_reuse_detected").
    - Sinon : marque `used_at`, émet un nouveau refresh dans la même `family_id`.
    """
    t = (
        db.query(RefreshToken)
        .filter_by(token_hash=_h(raw))
        .with_for_update()
        .first()
    )
    now = _now()
    if not t or (t.expires_at and t.expires_at < now):
        raise ValueError("invalid_refresh")

    if getattr(t, "used_at", None) is not None or getattr(t, "revoked_at", None) is not None:
        # REJEU DÉTECTÉ : révocation immédiate de toute la famille
        db.query(RefreshToken).filter_by(family_id=t.family_id).update(
            {"revoked_at": now}, synchronize_session=False
        )
        db.commit()
        raise ValueError("refresh_reuse_detected")

    t.used_at = now
    new_raw = issue_refresh(db, t.user_id, family_id=t.family_id)
    db.commit()
    return t.user_id, new_raw


class AuthService:

    def register(self, db: Session, dto: UserCreateDTO) -> TokenDTO:
        email = dto.email.lower().strip()

        if user_repository.email_exists(db, email):
            raise ValueError("Un utilisateur avec cet email existe déjà.")

        hashed = hash_password(dto.password)
        user = user_repository.create(
            db,
            email=email,
            password_hash=hashed,
            full_name=dto.full_name,
            role=dto.role,
        )
        logger.info("user_registered")
        return self._generate_tokens(db, user)

    def login(self, db: Session, dto: UserLoginDTO) -> TokenDTO:
        email = dto.email.lower().strip()

        # SEC-6 : Vérifier si le compte est temporairement verrouillé
        check_login_lockout(email)

        user = user_repository.get_by_email(db, email)
        if not user:
            # SEC-2 : Anti-énumération (temps constant)
            fake_verify(dto.password)
            record_login_failure(email)
            raise ValueError("Identifiants incorrects (email ou mot de passe invalide).")

        ok, needs_rehash = verify_password(user.password_hash, dto.password)
        if not ok:
            record_login_failure(email)
            raise ValueError("Identifiants incorrects (email ou mot de passe invalide).")

        # SEC-2 : Re-hachage transparent bcrypt -> Argon2id
        if needs_rehash:
            user.password_hash = hash_password(dto.password)
            db.flush()

        reset_login_failures(email)
        logger.info("user_login_ok")
        return self._generate_tokens(db, user)

    def refresh(self, db: Session, refresh_token: str) -> TokenDTO:
        user_id, new_raw = rotate_refresh(db, refresh_token)
        user = user_repository.get_by_id(db, str(user_id))
        if not user:
            raise ValueError("Utilisateur introuvable.")

        access_token = create_access_token(data={"sub": str(user.id)})
        logger.info("token_refreshed", extra={"user_id": str(user.id)})
        return TokenDTO(
            access_token=access_token,
            refresh_token=new_raw,
            token_type="bearer",
            user=UserResponseDTO(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                role=user.role,
            ),
        )

    def logout(self, db: Session, refresh_token: str) -> bool:
        ok = refresh_token_repository.revoke(db, refresh_token)
        db.commit()
        return ok

    def logout_all(self, db: Session, user_id: str) -> int:
        count = refresh_token_repository.revoke_all_for_user(db, user_id)
        db.commit()
        return count

    def get_user_by_id(self, db: Session, user_id: str):
        user = user_repository.get_by_id(db, user_id)
        if not user:
            return None
        return UserResponseDTO(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
        )

    def _generate_tokens(self, db: Session, user) -> TokenDTO:
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = issue_refresh(db, user_id=user.id)
        db.commit()

        return TokenDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponseDTO(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                role=user.role,
            ),
        )


auth_service = AuthService()
