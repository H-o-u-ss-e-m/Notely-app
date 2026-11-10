"""Rate limiting (slowapi + Redis / fallback mémoire) et verrouillage progressif (SEC-6)."""
import time
from typing import Dict, Tuple
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

_redis_client = None
_redis_checked = False


def _get_redis():
    import os
    if os.getenv("ENV") in ("test", "ci"):
        return None
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        import redis
        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.2, socket_timeout=0.2)
        client.ping()
        _redis_client = client
    except Exception:
        _redis_client = None
    return _redis_client


def get_client_ip(request: Request) -> str:
    """Extrait l'IP réelle derrière un reverse-proxy (X-Forwarded-For) ou l'adresse directe."""
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        first_ip = xff.split(",")[0].strip()
        if first_ip:
            return first_ip
    return get_remote_address(request) or "127.0.0.1"


def _resolve_storage_uri() -> str:
    if _get_redis() is not None:
        return settings.REDIS_URL
    return "memory://"


limiter = Limiter(key_func=get_client_ip, storage_uri=_resolve_storage_uri())


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "code": "RATE_LIMIT_EXCEEDED",
            "detail": f"Trop de requêtes : {exc.detail}",
        },
    )


# ── Verrouillage progressif du compte (SEC-6 : login_fail:{email.lower()}) ────
_mem_login_fails: Dict[str, Tuple[int, float]] = {}
_LOCKOUT_TTL = 900  # 15 minutes


def _fail_key(email: str) -> str:
    return f"login_fail:{(email or '').strip().lower()}"


def get_login_failures(email: str) -> int:
    key = _fail_key(email)
    r = _get_redis()
    if r is not None:
        try:
            val = r.get(key)
            return int(val) if val is not None else 0
        except Exception:
            pass
    entry = _mem_login_fails.get(key)
    if not entry:
        return 0
    count, exp = entry
    if time.time() > exp:
        _mem_login_fails.pop(key, None)
        return 0
    return count


def check_login_lockout(email: str) -> None:
    """Lève HTTP 429 avec Retry-After si le compte a >= 5 échecs consécutifs."""
    n = get_login_failures(email)
    if n >= 5:
        retry_after = min(900, 30 * (2 ** (n - 5)))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Compte temporairement verrouillé suite à plusieurs échecs. Réessayez dans {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )


def record_login_failure(email: str) -> int:
    """Incrémente le compteur d'échecs de connexion (TTL 900s) et retourne le total."""
    key = _fail_key(email)
    r = _get_redis()
    if r is not None:
        try:
            n = int(r.incr(key))
            r.expire(key, _LOCKOUT_TTL)
            return n
        except Exception:
            pass
    now = time.time()
    entry = _mem_login_fails.get(key)
    if not entry or now > entry[1]:
        n = 1
    else:
        n = entry[0] + 1
    _mem_login_fails[key] = (n, now + _LOCKOUT_TTL)
    return n


def reset_login_failures(email: str) -> None:
    """Réinitialise le compteur d'échecs après une connexion réussie."""
    key = _fail_key(email)
    r = _get_redis()
    if r is not None:
        try:
            r.delete(key)
        except Exception:
            pass
    _mem_login_fails.pop(key, None)
