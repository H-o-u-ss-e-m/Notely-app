"""Dépendances FastAPI partagées (authentification)."""
from typing import Optional

from fastapi import Header, HTTPException, status

from app.core.security import decode_access_token


def current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Retourne le user_id du JWT d'accès, sinon 401. Jamais de repli 'invité'."""
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization[7:].strip())
        if payload and payload.get("sub"):
            return str(payload["sub"])
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise",
        headers={"WWW-Authenticate": "Bearer"},
    )
