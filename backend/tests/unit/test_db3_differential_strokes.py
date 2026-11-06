"""Tests unitaires et d'intégration pour Chantier 4 (DB-3 : strokes PK UUID + client_id + PATCH/GET différentiel)."""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.db.models.course import Subject, Lesson, NotebookPage, Stroke
from app.core.security import create_access_token

client = TestClient(app)


def _auth_headers(user_id: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id})}"}


def test_stroke_model_has_uuid_pk_client_id_seq_and_deleted_at():
    """Vérifie que Stroke possède client_id, seq, deleted_at et que Lesson possède deleted_at."""
    assert hasattr(Stroke, "client_id")
    assert hasattr(Stroke, "seq")
    assert hasattr(Stroke, "deleted_at")
    assert hasattr(Lesson, "deleted_at")


def test_patch_and_get_strokes_differential_and_version_conflict():
    """
    Teste PATCH /api/v1/pages/{page_id}/strokes :
    - Ajout idempotent de tracés par client_id
    - Suppression logique (deleted_at) via removedClientIds
    - Incrément de page.version
    - Conflit 409 si baseVersion != page.version
    - GET /api/v1/pages/{page_id}/strokes ne renvoie que les tracés non supprimés triés par seq
    """
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    page_id = uuid.uuid4()
    lesson_id = uuid.uuid4()
    subject_id = uuid.uuid4()

    page = NotebookPage(
        id=page_id,
        lesson_id=lesson_id,
        page_number=1,
        width=794.0,
        height=1123.0,
        version=1,
    )
    strokes_store = []

    class FakeStrokeQuery:
        def __init__(self):
            self._removed_ids = None

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args):
            return self

        def all(self):
            active = [s for s in strokes_store if s.deleted_at is None]
            return sorted(active, key=lambda x: (x.seq or 0, x.start_time or 0.0))

    class FakeDB:
        def query(self, model):
            return FakeStrokeQuery()

        def add(self, obj):
            strokes_store.append(obj)

        def flush(self):
            pass

        def commit(self):
            pass

        def refresh(self, obj):
            pass

    from app.api.deps import get_owned_page

    def override_get_db():
        yield FakeDB()

    def override_get_owned_page(page_id: str):
        return page

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_owned_page] = override_get_owned_page
    try:
        # 1. PATCH avec baseVersion=1 : ajout de 2 tracés
        r1 = client.patch(
            f"/api/v1/pages/{page_id}/strokes",
            headers=_auth_headers(user_a),
            json={
                "baseVersion": 1,
                "added": [
                    {
                        "id": "client-s1",
                        "startTime": 10.0,
                        "endTime": 11.0,
                        "points": [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}],
                    },
                    {
                        "id": "client-s2",
                        "startTime": 12.0,
                        "endTime": 13.0,
                        "points": [{"x": 50.0, "y": 60.0}, {"x": 70.0, "y": 80.0}],
                    },
                ],
                "removedClientIds": [],
            },
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["version"] == 2
        assert len(strokes_store) == 2

        # 2. PATCH avec ancienne baseVersion=1 -> 409 Conflict
        r_conflict = client.patch(
            f"/api/v1/pages/{page_id}/strokes",
            headers=_auth_headers(user_a),
            json={"baseVersion": 1, "added": [], "removedClientIds": []},
        )
        assert r_conflict.status_code == 409

        # 3. PATCH avec baseVersion=2 : suppression logique de client-s1 + re-envoi idempotent de client-s2
        r2 = client.patch(
            f"/api/v1/pages/{page_id}/strokes",
            headers=_auth_headers(user_a),
            json={
                "baseVersion": 2,
                "added": [
                    {
                        "id": "client-s2",
                        "startTime": 12.0,
                        "endTime": 13.0,
                        "points": [{"x": 50.0, "y": 60.0}, {"x": 70.0, "y": 80.0}],
                    }
                ],
                "removedClientIds": ["client-s1"],
            },
        )
        assert r2.status_code == 200
        assert r2.json()["version"] == 3

        # 4. GET /api/v1/pages/{page_id}/strokes ne renvoie que client-s2
        r_get = client.get(
            f"/api/v1/pages/{page_id}/strokes",
            headers=_auth_headers(user_a),
        )
        assert r_get.status_code == 200
        body = r_get.json()
        assert body["version"] == 3
        assert [s["id"] for s in body["strokes"]] == ["client-s2"]
    finally:
        app.dependency_overrides.clear()
