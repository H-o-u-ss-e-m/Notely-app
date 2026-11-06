"""
Routeur Auth — /api/v1/auth/*
Utilise PostgreSQL via AuthService (plus aucun stockage en mémoire).
"""
from fastapi import APIRouter, HTTPException, status, Header, Depends
from typing import Optional
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import UserCreateDTO, UserLoginDTO, UserResponseDTO, TokenDTO, RefreshTokenRequestDTO
from app.modules.auth.service import auth_service
from app.core.security import decode_access_token

router = APIRouter()


@router.post("/auth/register", response_model=TokenDTO, status_code=status.HTTP_201_CREATED,
             summary="Inscription Utilisateur")
async def register(dto: UserCreateDTO, db: Session = Depends(get_db)):
    try:
        return auth_service.register(db, dto)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/auth/login", response_model=TokenDTO, summary="Connexion Utilisateur")
async def login(dto: UserLoginDTO, db: Session = Depends(get_db)):
    try:
        return auth_service.login(db, dto)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/auth/refresh", response_model=TokenDTO, summary="Rafraîchir les Tokens")
async def refresh(dto: RefreshTokenRequestDTO, db: Session = Depends(get_db)):
    try:
        return auth_service.refresh(db, dto.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Déconnexion")
async def logout(dto: RefreshTokenRequestDTO, db: Session = Depends(get_db)):
    auth_service.logout(db, dto.refresh_token)
    return None


@router.get("/auth/me", response_model=UserResponseDTO, summary="Profil Utilisateur Connecté")
async def get_me(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Header Authorization manquant")
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré")
    user = auth_service.get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return user
