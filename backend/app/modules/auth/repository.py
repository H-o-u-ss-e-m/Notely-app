"""
AuthRepository — Accès PostgreSQL pour les utilisateurs et refresh tokens (SEC-2 / SEC-3).
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.user import User, RefreshToken
from app.core.config import settings


class UserRepository:
    """Opérations CRUD sur la table users."""

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(
            User.email == email.lower().strip(),
            User.is_active == True  # noqa: E712
        ).first()

    def get_by_id(self, db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(
            User.id == user_id,
            User.is_active == True  # noqa: E712
        ).first()

    def create(self, db: Session, email: str, password_hash: str,
               full_name: Optional[str] = None, role: str = "student") -> User:
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name or email.split("@")[0],
            role=role,
        )
        db.add(user)
        db.flush()
        return user

    def email_exists(self, db: Session, email: str) -> bool:
        return db.query(User.id).filter(
            User.email == email.lower().strip()
        ).first() is not None


class RefreshTokenRepository:
    """Gestion des refresh tokens opaques avec rotation par famille (SEC-3)."""

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue(
        self,
        db: Session,
        user_id,
        family_id=None,
        expires_days: int = settings.REFRESH_TOKEN_EXPIRE_DAYS,
        user_agent: Optional[str] = None,
    ) -> str:
        raw = secrets.token_urlsafe(32)
        rt = RefreshToken(
            user_id=user_id,
            family_id=family_id or uuid.uuid4(),
            token_hash=self._hash(raw),
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
            user_agent=user_agent,
        )
        db.add(rt)
        db.flush()
        return raw

    def create(self, db: Session, user_id, token: str, expires_days: int = settings.REFRESH_TOKEN_EXPIRE_DAYS, family_id=None) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            family_id=family_id or uuid.uuid4(),
            token_hash=self._hash(token),
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
        )
        db.add(rt)
        db.flush()
        return rt

    def get_by_raw_for_update(self, db: Session, raw: str) -> Optional[RefreshToken]:
        h = self._hash(raw)
        return (
            db.query(RefreshToken)
            .filter_by(token_hash=h)
            .with_for_update()
            .first()
        )

    def revoke_family(self, db: Session, family_id) -> int:
        now = datetime.utcnow()
        return (
            db.query(RefreshToken)
            .filter_by(family_id=family_id)
            .update({"revoked_at": now}, synchronize_session=False)
        )

    def revoke(self, db: Session, token: str) -> bool:
        h = self._hash(token)
        rt = db.query(RefreshToken).filter_by(token_hash=h).first()
        if rt:
            now = datetime.utcnow()
            rt.revoked_at = now
            if getattr(rt, "family_id", None):
                self.revoke_family(db, rt.family_id)
            db.flush()
            return True
        return False

    def revoke_all_for_user(self, db: Session, user_id) -> int:
        """Révoque toutes les familles de sessions d'un utilisateur (logout-all)."""
        now = datetime.utcnow()
        count = (
            db.query(RefreshToken)
            .filter_by(user_id=user_id)
            .update({"revoked_at": now}, synchronize_session=False)
        )
        db.flush()
        return count


user_repository = UserRepository()
refresh_token_repository = RefreshTokenRepository()
