"""
Tests unitaires pour le repli VLM Cloud (ML-11 / §8.11).
Vérifie le respect strict du consentement, les garde-fous anti-hallucination,
le circuit breaker et les quotas utilisateurs.
"""
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

from app.services.vlm_fallback_service import VlmFallbackService
from app.ml.engines.base import LineOut, WordOut


@pytest.fixture
def vlm_service():
    return VlmFallbackService()


@pytest.fixture
def dummy_img():
    return Image.new("RGB", (200, 50), color=(255, 255, 255))


@pytest.fixture
def principal_line():
    return LineOut(
        text="Les fonctions continues",
        confidence=0.52,
        min_word_confidence=0.48,
        words=[
            WordOut(index=0, text="Les", confidence=0.55),
            WordOut(index=1, text="fonctions", confidence=0.50),
            WordOut(index=2, text="continues", confidence=0.51),
        ],
        alternatives=["Les fonctions derivables"],
        engine="trocr_fr",
        model_version="v3-fr",
    )


def test_vlm_without_consent_returns_principal(vlm_service, dummy_img, principal_line):
    """Sans consentement explicite, l'appel VLM est ignoré et le texte principal est retourné."""
    with patch.object(vlm_service, "call_vlm_provider") as mock_vlm:
        res = vlm_service.process_fallback(
            image=dummy_img,
            lang="fr",
            principal_line=principal_line,
            user_id="user_123",
            consent_cloud_ocr=False,  # Pas de consentement
        )
        assert res.text == principal_line.text
        assert res.engine == "trocr_fr"
        mock_vlm.assert_not_called()


def test_vlm_anti_hallucination_safeguard(vlm_service, dummy_img, principal_line):
    """
    Anti-hallucination (§8.11 #2) :
    Si CER(VLM, principal) > 0.60 et confiance_principale > 0.40,
    le texte principal est préservé et la transcription VLM est placée en alternative.
    """
    hallucinated_text = "Ceci est une hallucination totale du modèle vision langage sans rapport"
    with patch.object(vlm_service, "call_vlm_provider", return_value=hallucinated_text):
        res = vlm_service.process_fallback(
            image=dummy_img,
            lang="fr",
            principal_line=principal_line,
            user_id="user_123",
            consent_cloud_ocr=True,
        )
        # Le texte principal est maintenu
        assert res.text == principal_line.text
        assert res.engine == "trocr_fr"
        # Le texte VLM est présent dans les alternatives avec préfixe
        assert any("[VLM]" in alt for alt in res.alternatives)


def test_vlm_valid_replacement_marks_engine(vlm_service, dummy_img, principal_line):
    """
    Lorsque la transcription VLM est cohérente, elle remplace la prédiction
    et porte explicitement le marqueur engine='vlm'.
    """
    valid_text = "Les fonctions dérivables"  # Très proche du principal
    with patch.object(vlm_service, "call_vlm_provider", return_value=valid_text):
        res = vlm_service.process_fallback(
            image=dummy_img,
            lang="fr",
            principal_line=principal_line,
            user_id="user_123",
            consent_cloud_ocr=True,
        )
        assert res.text == valid_text
        assert res.engine == "vlm"
        assert res.confidence == 0.92


def test_vlm_circuit_breaker_tripping(vlm_service, dummy_img, principal_line):
    """Après 3 échecs consécutifs, le circuit breaker s'ouvre et bloque les requêtes suivantes."""
    assert not vlm_service.is_circuit_open()

    with patch.object(vlm_service, "call_vlm_provider", side_effect=RuntimeError("Timeout API")):
        # 3 échecs consécutifs
        vlm_service.process_fallback(dummy_img, "fr", principal_line, "user_1", True)
        vlm_service.process_fallback(dummy_img, "fr", principal_line, "user_1", True)
        vlm_service.process_fallback(dummy_img, "fr", principal_line, "user_1", True)

    assert vlm_service.is_circuit_open()

    # Requête suivante : court-circuitée immédiatement sans appeler call_vlm_provider
    with patch.object(vlm_service, "call_vlm_provider") as mock_vlm:
        res = vlm_service.process_fallback(dummy_img, "fr", principal_line, "user_1", True)
        assert res.text == principal_line.text
        mock_vlm.assert_not_called()


def test_vlm_user_daily_quota(vlm_service, dummy_img, principal_line):
    """Un utilisateur est plafonné à 50 appels VLM par jour."""
    # Consommer les 50 appels
    for _ in range(50):
        assert vlm_service.check_user_budget("user_budget_test") is True

    # Le 51ème est refusé
    assert vlm_service.check_user_budget("user_budget_test") is False
