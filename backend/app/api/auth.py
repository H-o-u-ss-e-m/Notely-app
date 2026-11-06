from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional
from app.schemas.auth import UserCreateDTO, UserLoginDTO, UserResponseDTO, TokenDTO, RefreshTokenRequestDTO
from app.services.auth_service import auth_service
from app.core.security import decode_access_token

router = APIRouter()

@router.post("/auth/register", response_model=TokenDTO, status_code=status.HTTP_201_CREATED, summary="Inscription Utilisateur")
async def register(dto: UserCreateDTO):
    try:
        return auth_service.register(dto)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/auth/login", response_model=TokenDTO, summary="Connexion Utilisateur")
async def login(dto: UserLoginDTO):
    try:
        return auth_service.login(dto)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.post("/auth/refresh", response_model=TokenDTO, summary="Rafraîchir les Tokens")
async def refresh(dto: RefreshTokenRequestDTO):
    try:
        return auth_service.refresh(dto.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.get("/auth/me", response_model=UserResponseDTO, summary="Profil Utilisateur Connecté")
async def get_me(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Header Authorization manquant ou invalide")
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token d'accès invalide ou expiré")
    user = auth_service.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return user
