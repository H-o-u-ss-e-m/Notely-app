"""
AuthService — Logique métier d'authentification avec PostgreSQL.
Remplace complètement l'ancien AuthService en mémoire.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.modules.auth.repository import user_repository, refresh_token_repository
from app.core.security import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token, decode_refresh_token
)
from app.schemas.auth import UserCreateDTO, UserLoginDTO, TokenDTO, UserResponseDTO

logger = logging.getLogger(__name__)


class AuthService:

    def register(self, db: Session, dto: UserCreateDTO) -> TokenDTO:
        email = dto.email.lower().strip()

        if user_repository.email_exists(db, email):
            raise ValueError("Un utilisateur avec cet email existe déjà.")

        hashed = get_password_hash(dto.password)
        user = user_repository.create(
            db, email=email, password_hash=hashed,
            full_name=dto.full_name, role=dto.role
        )
        logger.info("user_registered")
        return self._generate_tokens(db, user)

    def login(self, db: Session, dto: UserLoginDTO) -> TokenDTO:
        email = dto.email.lower().strip()
        user = user_repository.get_by_email(db, email)
        if not user or not verify_password(dto.password, user.password_hash):
            raise ValueError("Identifiants incorrects (email ou mot de passe invalide).")

        logger.info("user_login_ok")
        return self._generate_tokens(db, user)

    def refresh(self, db: Session, refresh_token: str) -> TokenDTO:
        # 1. Vérifier le token dans PostgreSQL
        rt_record = refresh_token_repository.get_valid(db, refresh_token)
        if not rt_record:
            raise ValueError("Refresh token invalide ou expiré.")

        # 2. Révoquer l'ancien token (rotation de token)
        refresh_token_repository.revoke(db, refresh_token)

        # 3. Récupérer l'utilisateur
        user = user_repository.get_by_id(db, str(rt_record.user_id))
        if not user:
            raise ValueError("Utilisateur introuvable.")

        logger.info("token_refreshed", extra={"user_id": str(user.id)})
        return self._generate_tokens(db, user)

    def logout(self, db: Session, refresh_token: str) -> bool:
        return refresh_token_repository.revoke(db, refresh_token)

    def get_user_by_id(self, db: Session, user_id: str):
        user = user_repository.get_by_id(db, user_id)
        if not user:
            return None
        return UserResponseDTO(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role
        )

    def _generate_tokens(self, db: Session, user) -> TokenDTO:
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # Persister le refresh token hashé en DB
        refresh_token_repository.create(db, user_id=user.id, token=refresh_token)

        return TokenDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponseDTO(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                role=user.role
            )
        )


auth_service = AuthService()
