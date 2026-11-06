"""
AuthRepository — Accès PostgreSQL pour les utilisateurs et refresh tokens.
"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.user import User, RefreshToken


class UserRepository:
    """Opérations CRUD sur la table users."""

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(
            User.email == email.lower().strip(),
            User.is_active == True
        ).first()

    def get_by_id(self, db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(
            User.id == user_id,
            User.is_active == True
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
        db.flush()   # Obtenir l'ID sans commit
        return user

    def email_exists(self, db: Session, email: str) -> bool:
        return db.query(User.id).filter(
            User.email == email.lower().strip()
        ).first() is not None


class RefreshTokenRepository:
    """Gestion des refresh tokens persistés."""

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create(self, db: Session, user_id, token: str, expires_days: int = 7) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            token_hash=self._hash(token),
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
        )
        db.add(rt)
        db.flush()
        return rt

    def get_valid(self, db: Session, token: str) -> Optional[RefreshToken]:
        h = self._hash(token)
        return db.query(RefreshToken).filter(
            RefreshToken.token_hash == h,
            RefreshToken.revoked_at == None,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()

    def revoke(self, db: Session, token: str) -> bool:
        h = self._hash(token)
        rt = db.query(RefreshToken).filter(RefreshToken.token_hash == h).first()
        if rt:
            rt.revoked_at = datetime.utcnow()
            db.flush()
            return True
        return False

    def revoke_all_for_user(self, db: Session, user_id) -> int:
        """Révoque toutes les sessions d'un utilisateur (logout complet)."""
        count = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at == None
        ).update({"revoked_at": datetime.utcnow()})
        return count


user_repository = UserRepository()
refresh_token_repository = RefreshTokenRepository()
