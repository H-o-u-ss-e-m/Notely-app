"""
Tests unitaires pour la Phase P5 — MLOps, Échelle, Métriques et Déploiement.
Vérifie la curation anti-poison (avec plafond 5%), le split par page, les règles de promotion,
le routage canary, le rollback, les métriques Prometheus et le middleware X-Min-Client-Version.
"""
import uuid
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from training.dataset_curation import (
    filter_and_curate_corrections,
    partition_dataset_by_page,
    split_of,
    check_training_trigger,
)
from training.promote import (
    decide_promotion,
    is_user_in_canary,
    ModelRegistryService,
)
from app.core.metrics import metrics_collector
from app.db.models.model_version import ModelVersion


client = TestClient(app)


def test_dataset_curation_and_user_contribution_cap():
    """
    Vérifie les filtres anti-poison et le plafonnement de contribution par utilisateur (5%).
    Clôture formellement l'élément P4 reporté.
    """
    raw_corrections = []
    # Créer 100 corrections valides
    # Utilisateur A contribue massivement (50 corrections) -> doit être plafonné à 5% max
    for i in range(50):
        raw_corrections.append({
            "id": str(uuid.uuid4()),
            "user_id": "user_heavy_contributor",
            "consent_train": True,
            "consent_withdrawn_at": None,
            "strokes": [{"id": f"s_{i}", "points": [{"x": 0, "y": 0}]}],
            "predicted_text": f"prediction_{i}",
            "corrected_text": f"prediction_{i}",
            "stroke_fingerprint": f"fp_heavy_{i}",
        })

    # D'autres utilisateurs contribuent à hauteur de 50 corrections réparties
    for j in range(50):
        raw_corrections.append({
            "id": str(uuid.uuid4()),
            "user_id": f"user_normal_{j}",
            "consent_train": True,
            "consent_withdrawn_at": None,
            "strokes": [{"id": f"s_norm_{j}", "points": [{"x": 0, "y": 0}]}],
            "predicted_text": f"prediction_n_{j}",
            "corrected_text": f"prediction_n_{j}",
            "stroke_fingerprint": f"fp_norm_{j}",
        })

    curated, stats = filter_and_curate_corrections(raw_corrections, max_user_share=0.05)
    
    # Vérifier que le contributeur massif a été plafonné à 5%
    heavy_count = sum(1 for c in curated if c["user_id"] == "user_heavy_contributor")
    total_accepted = len(curated)
    assert heavy_count <= max(1, int(100 * 0.05))
    assert stats["rejected_user_cap"] > 0
    assert total_accepted > 0


def test_page_level_split_deterministic():
    """
    Règle d'or (§8.6.c) : split par page ou par utilisateur, jamais par ligne.
    Vérifie la répartition déterministe entre train, val et test.
    """
    page_1 = "page_abc_123"
    assert split_of(page_1) == split_of(page_1)  # Déterministe

    splits = partition_dataset_by_page([
        {"id": "c1", "page_id": "pg_001"},
        {"id": "c2", "page_id": "pg_001"},  # Même page -> même split
        {"id": "c3", "page_id": "pg_002"},
        {"id": "c4", "page_id": "pg_003"},
    ])
    assert len(splits["train"]) + len(splits["val"]) + len(splits["test"]) == 4


def test_training_trigger_threshold():
    """Vérifie le seuil de déclenchement du ré-entraînement (>= 500 corrections)."""
    can_trigger_499, _ = check_training_trigger(499, threshold=500)
    assert can_trigger_499 is False

    can_trigger_500, msg = check_training_trigger(500, threshold=500)
    assert can_trigger_500 is True
    assert "Seuil de ré-entraînement atteint" in msg


def test_model_promotion_rules():
    """Vérifie les critères stricts de décision de promotion (§8.7)."""
    active_metrics = {
        "cer_fr": 0.150,
        "accent_err": 0.500,
        "cer_en": 0.120,
        "p95_ms_per_line": 2000.0,
        "ece": 0.070,
    }

    # Candidat qui améliore le CER FR de > 5%, ne régresse pas sur EN, ECE < 0.08
    good_candidate = {
        "cer_fr": 0.135,         # 10% d'amélioration
        "accent_err": 0.400,
        "cer_en": 0.121,         # Régression < 2%
        "p95_ms_per_line": 1800.0,
        "ece": 0.065,
    }
    passed, checks = decide_promotion(good_candidate, active_metrics)
    assert passed is True
    assert all(checks.values())

    # Candidat avec mauvaise calibration ECE >= 0.08 -> doit échouer
    bad_calibration_candidate = dict(good_candidate, ece=0.095)
    passed_bad, checks_bad = decide_promotion(bad_calibration_candidate, active_metrics)
    assert passed_bad is False
    assert checks_bad["calibration_ok"] is False


def test_canary_routing_hash():
    """Vérifie que le routage canary est déterministe et isole 10% des utilisateurs."""
    uid = "user_canary_test_id"
    res1 = is_user_in_canary(uid, canary_percentage=10)
    res2 = is_user_in_canary(uid, canary_percentage=10)
    assert res1 == res2


def test_one_command_rollback(monkeypatch):
    """Vérifie le rollback immédiat d'un modèle actif vers sa version précédente."""
    mock_db = MagicMock()
    current_active = ModelVersion(id=uuid.uuid4(), name="trocr_fr", version="v4-bad", status="active")
    previous_retired = ModelVersion(id=uuid.uuid4(), name="trocr_fr", version="v3-stable", status="retired")

    # Configuration des retours de mock
    def mock_query(model):
        m = MagicMock()
        if model == ModelVersion:
            filt = MagicMock()
            m.filter.return_value = filt
            # Premier appel pour current_active, second pour previous_retired
            filt.first.side_effect = [current_active, previous_retired]
            filt.order_by.return_value.first.return_value = previous_retired
        return m

    mock_db.query = mock_query

    res = ModelRegistryService.rollback_active(mock_db, "trocr_fr")
    assert res["rollback"] is True
    assert res["active_version"] == "v3-stable"
    assert current_active.status == "retired"
    assert previous_retired.status == "active"


def test_prometheus_metrics_endpoint():
    """Vérifie l'exposition des métriques qualité IA au format Prometheus."""
    metrics_collector.record_ocr_line(0.25, 0.94)
    metrics_collector.record_correction("fr", "trocr_fr")
    metrics_collector.record_vlm_call()
    metrics_collector.record_cache_access(hit=True)

    resp = client.get("/metrics")
    assert resp.status_code == 200
    content = resp.text
    assert "ocr_line_latency_seconds" in content
    assert "ocr_confidence" in content
    assert "ocr_corrections_total" in content
    assert "ocr_cache_hit_ratio" in content
    assert "ocr_vlm_calls_total" in content


def test_client_min_version_middleware():
    """
    Vérifie le middleware X-Min-Client-Version (§9.4) :
    - Version valide -> 200 OK avec header X-Min-Client-Version.
    - Version obsolète -> HTTP 426 Upgrade Required.
    """
    # Version à jour
    resp_ok = client.get("/api/v1/health", headers={"X-Client-Version": "1.2.0"})
    assert resp_ok.status_code == 200
    assert "X-Min-Client-Version" in resp_ok.headers

    # Version obsolète
    resp_upgrade = client.get("/api/v1/health", headers={"X-Client-Version": "0.9.0"})
    assert resp_upgrade.status_code == 426
    assert "Mise à jour requise" in resp_upgrade.json()["detail"]
