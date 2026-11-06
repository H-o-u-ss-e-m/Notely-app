"""Middleware ASGI : request_id par requete (X-Request-ID) + log d'acces sans donnees personnelles."""
import logging
import re
import time
import uuid

from app.core.logging import request_id_var

logger = logging.getLogger("access")
_VALID_ID = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")


class RequestIdMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        rid = incoming if _VALID_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(rid)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", [])
                message["headers"] = list(message["headers"]) + [(b"x-request-id", rid.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            # path sans query string (peut contenir des identifiants) ; jamais de corps.
            logger.info("request", extra={
                "method": scope.get("method"), "path": scope.get("path"),
                "status_code": status,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            })
            request_id_var.reset(token)
