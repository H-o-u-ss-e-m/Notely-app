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


# -- Chantier 3 (Plan v2 §5.1 - §5.6) : Argon2id, Refresh Rotation, Anti-IDOR, Lockout, CORS, Code mort --

def test_sec2_argon2id_and_transparent_bcrypt_rehash():
    import bcrypt
    from app.core.security import hash_password, verify_password, fake_verify

    # 1. Nouveau hash = Argon2id
    h_argon = hash_password("MonSuperMotDePasse!2026")
    assert h_argon.startswith("$argon2id$")
    ok, needs_rehash = verify_password(h_argon, "MonSuperMotDePasse!2026")
    assert ok is True
    assert needs_rehash is False

    ok_bad, _ = verify_password(h_argon, "MauvaisMotDePasse")
    assert ok_bad is False

    # 2. Ancien hash bcrypt -> reconnu + needs_rehash = True
    h_bcrypt = bcrypt.hashpw(b"AncienMotDePasse", bcrypt.gensalt()).decode("utf-8")
    ok_bc, rehash_bc = verify_password(h_bcrypt, "AncienMotDePasse")
    assert ok_bc is True
    assert rehash_bc is True

    # 3. Anti-énumération fake_verify
    fake_verify("n'importe quoi")


def test_sec3_refresh_rotation_and_reuse_detection():
    import uuid
    from app.modules.auth.service import issue_refresh, rotate_refresh
    from app.db.models.user import RefreshToken

    store = []

    class FakeQuery:
        def __init__(self, items, filters=None):
            self.items = items
            self.filters = filters or {}

        def filter_by(self, **kwargs):
            f = dict(self.filters)
            f.update(kwargs)
            return FakeQuery(self.items, f)

        def filter(self, *args):
            return self

        def with_for_update(self):
            return self

        def _matched(self):
            res = []
            for it in self.items:
                match = True
                for k, v in self.filters.items():
                    if getattr(it, k, None) != v:
                        match = False
                        break
                if match:
                    res.append(it)
            return res

        def first(self):
            m = self._matched()
            return m[0] if m else None

        def update(self, values: dict, synchronize_session=False):
            m = self._matched()
            for it in m:
                for k, v in values.items():
                    setattr(it, k, v)
            return len(m)

    class FakeSession:
        def add(self, obj):
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            store.append(obj)

        def flush(self):
            pass

        def commit(self):
            pass

        def query(self, model):
            return FakeQuery(store)

    db = FakeSession()
    uid = uuid.uuid4()

    # 1. Émission initiale
    raw1 = issue_refresh(db, uid)
    assert len(store) == 1
    fam_id = store[0].family_id
    assert fam_id is not None

    # 2. Rotation normale : raw1 -> raw2 dans la même famille
    ret_uid, raw2 = rotate_refresh(db, raw1)
    assert ret_uid == uid
    assert raw2 != raw1
    assert len(store) == 2
    assert store[0].used_at is not None
    assert store[1].family_id == fam_id
    assert store[1].revoked_at is None

    # 3. REJEU de raw1 -> détecté, toute la famille (dont raw2) est révoquée !
    with pytest.raises(ValueError, match="refresh_reuse_detected"):
        rotate_refresh(db, raw1)

    assert store[0].revoked_at is not None
    assert store[1].revoked_at is not None

    # 4. raw2 ne peut plus être utilisé non plus
    with pytest.raises(ValueError, match="refresh_reuse_detected"):
        rotate_refresh(db, raw2)


def test_sec4_anti_idor_deps_returns_404_for_other_user():
    from fastapi import HTTPException
    from app.api.deps import get_owned_page, get_owned_lesson, get_owned_subject

    db = MagicMock()
    # Simuler qu'aucune ressource n'appartient à user B
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.join.return_value.filter.return_value.first.return_value = None
    db.query.return_value.join.return_value.join.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_subj:
        get_owned_subject("22222222-2222-2222-2222-222222222222", uid="user-B", db=db)
    assert exc_subj.value.status_code == 404

    with pytest.raises(HTTPException) as exc_les:
        get_owned_lesson("22222222-2222-2222-2222-222222222222", uid="user-B", db=db)
    assert exc_les.value.status_code == 404

    with pytest.raises(HTTPException) as exc_page:
        get_owned_page("22222222-2222-2222-2222-222222222222", uid="user-B", db=db)
    assert exc_page.value.status_code == 404


def test_sec6_progressive_login_lockout():
    from fastapi import HTTPException
    from app.core.ratelimit import check_login_lockout, record_login_failure, reset_login_failures

    email = "lockout-test@example.com"
    reset_login_failures(email)

    # 4 échecs : pas encore verrouillé
    for _ in range(4):
        record_login_failure(email)
    check_login_lockout(email)  # ne lève pas

    # 5e échec : verrouillage progressif (HTTP 429 + Retry-After)
    record_login_failure(email)
    with pytest.raises(HTTPException) as exc:
        check_login_lockout(email)
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) >= 30

    # Reset après succès
    reset_login_failures(email)
    check_login_lockout(email)


def test_sec7_cors_disallows_ngrok_regex_bypass():
    r = client.options(
        "/api/v1/health",
        headers={"Origin": "https://attacker.ngrok-free.app", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in r.headers


def test_sec56_dead_code_removed():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert not os.path.exists(os.path.join(root, "app", "api", "auth.py"))
    assert not os.path.exists(os.path.join(root, "app", "ml", "preprocessing.py"))

