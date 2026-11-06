from datetime import datetime, timedelta
from typing import Optional
import secrets
import uuid
import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from jose import JWTError, jwt

from app.core.config import settings  # noqa: E402

SECRET_KEY = settings.JWT_SECRET_KEY
REFRESH_SECRET_KEY = settings.JWT_SECRET_KEY + "-refresh"
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# SEC-2 : Argon2id avec re-hachage transparent des anciens hash bcrypt
ph = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=2)
_DUMMY_HASH = ph.hash("notely-dummy-password")


def hash_password(pw: str) -> str:
    return ph.hash(pw)


get_password_hash = hash_password


def verify_password(stored: str, pw: str) -> tuple[bool, bool]:
    """Vérifie le mot de passe et retourne (ok, needs_rehash)."""
    if not stored or not pw:
        return False, False
    # Compatibilité au cas où l'appelant inverserait (plain, hash)
    if not (stored.startswith("$argon2") or stored.startswith("$2")) and (
        pw.startswith("$argon2") or pw.startswith("$2")
    ):
        stored, pw = pw, stored

    if stored.startswith("$2"):
        try:
            ok = bcrypt.checkpw(pw.encode("utf-8"), stored.encode("utf-8"))
            return ok, ok
        except Exception:
            return False, False

    try:
        ph.verify(stored, pw)
        return True, ph.check_needs_rehash(stored)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False, False


def fake_verify(pw: str) -> None:
    """Anti-énumération : consomme le même temps CPU qu'un vrai Argon2id."""
    try:
        ph.verify(_DUMMY_HASH, pw)
    except Exception:
        pass


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": uuid.uuid4().hex,
            "type": "access",
        }
    )
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: Optional[dict] = None, expires_delta: Optional[timedelta] = None) -> str:
    """SEC-3 : Refresh token opaque 256 bits (stocké haché SHA-256 en base)."""
    return secrets.token_urlsafe(32)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


def extract_user_id_from_header(authorization: Optional[str]) -> str:
    """
    Extrait le user_id depuis le Header HTTP Authorization Bearer <token>.
    Retourne 'usr-guest' par défaut si non authentifié.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            return payload["sub"]
    return "usr-guest"
