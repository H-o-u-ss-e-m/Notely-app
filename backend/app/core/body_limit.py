"""Middleware ASGI : limite la taille du corps des requêtes (anti-DoS)."""
import json


class BodySizeLimitMiddleware:
    """Refuse (413) les requêtes dont le corps dépasse `max_bytes`.

    Vérifie l'en-tête Content-Length, puis compte les octets réellement reçus
    (couvre le transfert chunked sans Content-Length).
    """

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send, status=400, message="Content-Length invalide")
                return

        received = 0
        too_large = False

        async def limited_receive():
            nonlocal received, too_large
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    too_large = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        response_started = False

        async def guarded_send(message):
            nonlocal response_started
            if too_large and not response_started:
                response_started = True
                await self._reject(send)
                return
            if too_large:
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        await self.app(scope, limited_receive, guarded_send)

    @staticmethod
    async def _reject(send, status: int = 413, message: str = "Requête trop volumineuse"):
        from app.core.errors import error_body  # import tardif : evite un cycle a l'import

        code = "PAYLOAD_TOO_LARGE" if status == 413 else "BAD_REQUEST"
        body = json.dumps(error_body(code, message)).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode())],
        })
        await send({"type": "http.response.body", "body": body})
