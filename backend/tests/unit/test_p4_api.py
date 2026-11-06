import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ocr_feedback import router as feedback_router
from app.api.me import router as me_router
from app.api.ocr_jobs import router as jobs_router
from app.db.session import get_db
from app.core.security import create_access_token
from app.db.models.user import User
from app.db.models.user_settings import UserSettings
from app.db.models.user_dictionary import UserDictionary
from app.db.models.ocr_correction import OcrCorrection
from app.db.models.ocr_job import OcrJob

app = FastAPI()
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")

USER_A_ID = str(uuid.uuid4())
USER_B_ID = str(uuid.uuid4())


def _auth_header(user_id: str):
    token = create_access_token({"sub": user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_db():
    mock = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


client = TestClient(app)


def test_feedback_anti_poison_rejected(mock_db):
    headers = _auth_header(USER_A_ID)
    payload = {
        "stroke_ids": ["s1"],
        "predicted_text": "derivable",
        "corrected_text": "zzzzzzzzzzzzzz",  # Spam pattern
        "scope": "word",
    }
    response = client.post("/api/v1/ocr/feedback", json=payload, headers=headers)
    assert response.status_code == 422
    assert "anti-spam" in response.text


def test_feedback_server_consent_train_enforced(mock_db):
    headers = _auth_header(USER_A_ID)

    # Simuler des paramètres utilisateur avec consent_train=False sur le serveur
    user_settings = UserSettings(user_id=uuid.UUID(USER_A_ID), consent_train=False)

    def mock_query(model):
        q = MagicMock()
        if model == UserSettings:
            q.filter.return_value.first.return_value = user_settings
        elif model == UserDictionary:
            q.filter.return_value.first.return_value = None
        return q

    mock_db.query.side_effect = mock_query

    # L'utilisateur envoie consent_train=True dans sa requête cliente
    payload = {
        "stroke_ids": ["s1"],
        "strokes": [{"id": "s1", "points": [{"x": 1.0, "y": 2.0}]}],
        "predicted_text": "derivable",
        "corrected_text": "dérivable",
        "scope": "word",
        "consent_train": True,
    }

    response = client.post("/api/v1/ocr/feedback", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Vérifier que le serveur a ajouté une correction avec consent_train=False (minimisation RGPD)
    added_objs = [call[0][0] for call in mock_db.add.call_args_list]
    correction_obj = [o for o in added_objs if isinstance(o, OcrCorrection)][0]
    assert correction_obj.consent_train is False
    assert correction_obj.strokes_json is None  # Pas de tracés stockés sans consentement serveur


def test_corrections_anti_idor(mock_db):
    headers_a = _auth_header(USER_A_ID)

    # Simuler 1 correction appartenant à User A
    c1 = OcrCorrection(
        id=uuid.uuid4(),
        user_id=uuid.UUID(USER_A_ID),
        predicted_text="pred",
        corrected_text="corr",
        language="fr",
        engine="trocr_fr",
        confidence=0.8,
        consent_train=False,
        created_at=datetime.utcnow(),
    )

    query_mock = MagicMock()
    mock_db.query.return_value = query_mock
    filter_mock = MagicMock()
    query_mock.filter.return_value = filter_mock
    filter_mock.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [c1]
    filter_mock.count.return_value = 1

    resp = client.get("/api/v1/ocr/corrections", headers=headers_a)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["corrections"][0]["predicted_text"] == "pred"


def test_me_settings_lifecycle(mock_db):
    headers = _auth_header(USER_A_ID)
    user = User(id=uuid.UUID(USER_A_ID), email="user_a@test.com", password_hash="hash")
    settings = UserSettings(
        user_id=uuid.UUID(USER_A_ID),
        consent_train=False,
        consent_cloud_ocr=False,
        ocr_language="fr",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Mock query pour _require_user et UserSettings
    def mock_query(model):
        m = MagicMock()
        if model == User:
            m.filter.return_value.first.return_value = user
        elif model == UserSettings:
            m.filter.return_value.first.return_value = settings
        return m

    mock_db.query.side_effect = mock_query

    # 1. GET settings
    resp = client.get("/api/v1/me/settings", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["consent_train"] is False

    # 2. PUT settings (opt-in)
    update_payload = {"consent_train": True, "consent_cloud_ocr": True}
    resp_put = client.put("/api/v1/me/settings", json=update_payload, headers=headers)
    assert resp_put.status_code == 200
    assert settings.consent_train is True
    assert settings.consent_cloud_ocr is True


def test_me_export_zip_and_json(mock_db):
    headers = _auth_header(USER_A_ID)
    user = User(id=uuid.UUID(USER_A_ID), email="user_a@test.com", password_hash="hash")

    def mock_query(model):
        m = MagicMock()
        if model == User:
            m.filter.return_value.first.return_value = user
        else:
            m.filter.return_value.all.return_value = []
        return m

    mock_db.query.side_effect = mock_query

    # 1. Format ZIP par défaut (§4.8)
    resp_zip = client.get("/api/v1/me/export", headers=headers)
    assert resp_zip.status_code == 200
    assert resp_zip.headers["content-type"] == "application/zip"
    assert "attachment; filename=" in resp_zip.headers.get("content-disposition", "")
    assert len(resp_zip.content) > 100  # Archive ZIP non vide

    # 2. Format JSON explicite
    resp_json = client.get("/api/v1/me/export?format=json", headers=headers)
    assert resp_json.status_code == 200
    assert "user" in resp_json.json()
    assert resp_json.json()["user"]["email"] == "user_a@test.com"


def test_line_memory_survives_restart(mock_db):
    from app.domain.line_memory import line_memory
    user_id = USER_A_ID
    fp = "fp-test-restart-123"
    corrected_text = "Théorème de Pythagore vérifié"

    # 1. Mise en cache et lecture
    line_memory.store(user_id, fp, corrected_text)
    assert line_memory.lookup(user_id, fp) == corrected_text

    # 2. Simulation d'un redémarrage complet du serveur (cache mémoire vidé)
    line_memory.clear()
    assert line_memory.count() == 0

    # 3. Simuler la persistance en base dans ocr_corrections (source de vérité)
    corr_record = OcrCorrection(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        stroke_fingerprint=fp,
        line_corrected=corrected_text,
        predicted_text="Theoreme",
        corrected_text=corrected_text,
        language="fr",
        engine="trocr_fr",
        consent_train=False,
    )

    with patch("app.db.session.SessionLocal") as mock_sess_cls:
        sess_mock = MagicMock()
        sess_mock.query.return_value.filter.return_value.order_by.return_value.first.return_value = corr_record
        mock_sess_cls.return_value.__enter__.return_value = sess_mock

        # Le lookup doit interroger la DB, restaurer la valeur et repeupler le cache
        res = line_memory.lookup(user_id, fp)
        assert res == corrected_text
        assert line_memory.count() == 1  # Réinjecté en cache local!


def test_ocr_jobs_lifecycle_and_anti_idor(mock_db):
    headers_a = _auth_header(USER_A_ID)
    headers_b = _auth_header(USER_B_ID)

    job_id = uuid.uuid4()
    job = OcrJob(
        id=job_id,
        user_id=uuid.UUID(USER_A_ID),
        status="completed",
        progress=1.0,
        result_json={"text": "résultat OCR"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # 1. Création d'un job -> 202 Accepted
    create_payload = {
        "strokes": [
            {
                "id": "s1",
                "points": [{"x": 10.0, "y": 10.0}, {"x": 50.0, "y": 10.0}],
                "startTime": 0.0,
                "endTime": 1.0,
            }
        ],
        "canvasWidth": 800.0,
        "canvasHeight": 1000.0,
        "options": {"language": "fr"},
    }

    with patch("app.api.ocr_jobs.dispatch_ocr_job"):
        resp_post = client.post("/api/v1/ocr/jobs", json=create_payload, headers=headers_a)
        assert resp_post.status_code == 202
        assert resp_post.json()["status"] == "pending"
        assert "job_id" in resp_post.json()

    # 2. Consultation par le propriétaire (User A) -> 200 OK
    mock_db.query.return_value.filter.return_value.first.return_value = job
    resp_get = client.get(f"/api/v1/ocr/jobs/{job_id}", headers=headers_a)
    assert resp_get.status_code == 200
    assert resp_get.json()["status"] == "completed"
    assert resp_get.json()["progress"] == 1.0

    # 3. Anti-IDOR : consultation par User B -> 404
    resp_get_b = client.get(f"/api/v1/ocr/jobs/{job_id}", headers=headers_b)
    assert resp_get_b.status_code == 404
