"""Erreurs metier + handlers uniformes.

Format : {"error": {"code", "message", "requestId", "details"}}.
Compatibilite : la cle historique "detail" (FastAPI) est conservee a cote de "error",
car les clients Flutter/Angular actuels lisent `detail`.
"""
import logging
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import request_id_var

logger = logging.getLogger("errors")

_STATUS_CODES = {
    400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED", 409: "CONFLICT", 413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR", 429: "RATE_LIMITED",
}


class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"

    def __init__(self, message: str, *, details: Any = None):
        super().__init__(message)
        self.message, self.details = message, details


class NotFound(AppError):
    status_code, code = 404, "NOT_FOUND"


class Forbidden(AppError):
    status_code, code = 403, "FORBIDDEN"


class Conflict(AppError):
    status_code, code = 409, "CONFLICT"


class PayloadTooLarge(AppError):
    status_code, code = 413, "PAYLOAD_TOO_LARGE"


class OcrFailed(AppError):
    status_code, code = 502, "OCR_FAILED"


def error_body(code: str, message: str, details: Any = None, detail: Any = None) -> dict:
    return {
        "error": {"code": code, "message": message,
                  "requestId": request_id_var.get(), "details": details},
        "detail": detail if detail is not None else message,
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code,
                            content=error_body(exc.code, exc.message, exc.details))

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Erreur"
        code = _STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(error_body(code, message, detail=exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        # On ne renvoie que loc/msg/type : jamais la valeur fautive (peut contenir des traces).
        details = [{"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")}
                   for e in errors]
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(error_body(
                "VALIDATION_ERROR", "Donnees de requete invalides.", details, detail=details)),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception")
        return JSONResponse(status_code=500, content=error_body("INTERNAL", "Erreur interne."))
