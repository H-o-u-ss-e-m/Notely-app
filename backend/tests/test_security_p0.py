"""Tests P0 - securite : config, authentification, limites, anti-IDOR."""
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import config
from app.core.body_limit import BodySizeLimitMiddleware
from app.core.security import create_access_token, decode_access_token
from app.main import app
from app.modules.courses.repository import PageRepository, StrokeIdConflict

client = TestClient(app)


def _auth_headers(user_id: str = "11111111-1111-1111-1111-111111111111") -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id})}"}


def _stroke(sid: str = "s1", n_points: int = 3) -> dict:
    return {
        "id": sid, "startTime": 0, "endTime": 1,
        "points": [{"x": float(i), "y": float(i)} for i in range(n_points)],
    }


# -- Configuration ----------------------------------------------------------

def test_missing_jwt_secret_refuses_to_start(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(config.ConfigError, match="JWT_SECRET_KEY"):
        config._load_jwt_secret()


def test_short_jwt_secret_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "short")
    with pytest.raises(config.ConfigError):
        config._load_jwt_secret()


@pytest.mark.parametrize("known", sorted(config._COMPROMISED_JWT_SECRETS))
def test_compromised_jwt_secret_rejected(monkeypatch, known):
    monkeypatch.setenv("JWT_SECRET_KEY", known)
    with pytest.raises(config.ConfigError):
        config._load_jwt_secret()


def test_cors_wildcard_rejected(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(config.ConfigError):
        config._load_cors_origins("dev")


def test_cors_prod_requires_https(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://example.com")
    with pytest.raises(config.ConfigError):
        config._load_cors_origins("prod")


def test_cors_accepts_json_and_csv(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["http://a.test","http://b.test"]')
    assert config._load_cors_origins("dev") == ["http://a.test", "http://b.test"]
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    assert config._load_cors_origins("dev") == ["http://a.test", "http://b.test"]


def test_cors_disallowed_origin_gets_no_header():
    r = client.options(
        "/api/v1/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in r.headers


# -- Authentification -------------------------------------------------------

OCR_ROUTES = ["/api/v1/recognition", "/api/v1/segmentation", "/api/v1/structural-htr",
              "/api/v1/export-pdf-raw", "/api/recognition", "/api/segmentation"]


@pytest.mark.parametrize("path", OCR_ROUTES)
def test_ocr_routes_require_auth(path):
    assert client.post(path, json={"strokes": []}).status_code == 401


def test_invalid_token_rejected():
    r = client.post("/api/v1/recognition", json={"strokes": []},
                    headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_health_stays_public():
    assert client.get("/api/v1/health").status_code == 200


def test_authenticated_empty_recognition_ok():
    r = client.post("/api/v1/recognition", json={"strokes": []}, headers=_auth_headers())
    assert r.status_code == 200 and r.json()["lineCount"] == 0


def test_access_token_has_iat_and_jti():
    payload = decode_access_token(create_access_token({"sub": "u"}))
    assert payload and payload["iat"] and payload["jti"] and payload["type"] == "access"


# -- Limites (anti-DoS) -----------------------------------------------------

def test_too_many_strokes_rejected_422():
    body = {"strokes": [_stroke(f"s{i}", 2) for i in range(5_001)]}
    assert client.post("/api/v1/segmentation", json=body, headers=_auth_headers()).status_code == 422


def test_too_many_points_in_stroke_rejected_422():
    body = {"strokes": [_stroke("s1", 10_001)]}
    assert client.post("/api/v1/segmentation", json=body, headers=_auth_headers()).status_code == 422


def test_too_many_total_points_rejected_422():
    body = {"strokes": [_stroke(f"s{i}", 5_000) for i in range(41)]}  # 205 000 points
    assert client.post("/api/v1/segmentation", json=body, headers=_auth_headers()).status_code == 422


def test_absurd_coordinates_rejected_422():
    s = _stroke()
    s["points"][0]["x"] = 1e9
    r = client.post("/api/v1/segmentation", json={"strokes": [s]}, headers=_auth_headers())
    assert r.status_code == 422


def test_canvas_dimension_limit():
    r = client.post("/api/v1/segmentation", json={"strokes": [], "canvasWidth": 10**6},
                    headers=_auth_headers())
    assert r.status_code == 422


def _limited_app(max_bytes: int) -> TestClient:
    a = FastAPI()
    a.add_middleware(BodySizeLimitMiddleware, max_bytes=max_bytes)

    @a.post("/echo")
    async def echo(payload: dict):
        return {"ok": True}

    return TestClient(a)


def test_body_limit_rejects_large_content_length():
    r = _limited_app(100).post("/echo", json={"x": "a" * 500})
    assert r.status_code == 413


def test_body_limit_rejects_chunked_without_content_length():
    def gen():
        yield b'{"x": "'
        yield b"a" * 500
        yield b'"}'

    r = _limited_app(100).post("/echo", content=gen(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_body_limit_allows_small_body():
    assert _limited_app(1000).post("/echo", json={"x": "a"}).status_code == 200


# -- Anti-IDOR sur les traces -----------------------------------------------

def _page_with(existing_ids):
    page = MagicMock()
    page.id = "page-A"
    page.version = 1
    page.strokes = [MagicMock(id=i) for i in existing_ids]
    return page


def test_stroke_id_owned_by_another_page_is_rejected():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = ("victim-stroke",)
    with pytest.raises(StrokeIdConflict):
        PageRepository().save_strokes(db, _page_with([]), [{"id": "victim-stroke", "points": []}])
    db.add.assert_not_called()


def test_own_stroke_ids_are_not_flagged():
    db = MagicMock()
    page = _page_with(["mine"])
    PageRepository().save_strokes(db, page, [{"id": "mine", "points": []}])
    db.query.assert_not_called()  # aucun ID etranger : pas de requete de collision
