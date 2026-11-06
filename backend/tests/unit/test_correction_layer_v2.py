"""
Tests d'acceptation Partie 1 & 2.4 (NOTELY — Plan d'amélioration v2) :
- normalize_key (arabe : tashkeel, tatweel, variantes d'alef, ى/ي, ة/ه ; latin : casefold)
- ink_hash tolérant (grille 32x8, distance de Hamming <= 12)
- should_reject / validate_correction conscient du moteur et de la langue (arabe non rejeté à tort, codes d'erreur lisibles)
- CorrectionLayer appliquée EN DERNIER après le cache HTR (mémoire de ligne exacte + proche, dictionnaire dès la 1re correction)
- Persistance et fonctionnement même si consent_train = False
- test_feedback_then_recognize_returns_correction pour fr, en, ar
"""
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.schemas.strokes import Stroke, Point
from app.ml.engines.base import LineOut, WordOut


def _make_strokes(offset_x: float = 0.0, offset_y: float = 0.0, jitter: float = 0.0):
    return [
        Stroke(
            id="s1",
            points=[
                Point(x=10.0 + offset_x, y=20.0 + offset_y),
                Point(x=40.0 + offset_x + jitter, y=22.0 + offset_y),
                Point(x=80.0 + offset_x, y=20.0 + offset_y + jitter),
            ],
            startTime=1.0,
            endTime=2.0,
        ),
        Stroke(
            id="s2",
            points=[
                Point(x=90.0 + offset_x, y=18.0 + offset_y),
                Point(x=130.0 + offset_x, y=25.0 + offset_y),
            ],
            startTime=2.5,
            endTime=3.5,
        ),
    ]


def test_normalize_key_arabic_and_latin():
    from app.domain.correction_layer import normalize_key

    # Variantes d'alef, tashkeel, tatweel, ة/ه, ى/ي
    assert normalize_key("مَرْحَبًا", "ar") == normalize_key("مرحبا", "ar")
    assert normalize_key("أحمد", "ar") == normalize_key("إحمد", "ar") == normalize_key("احمد", "ar")
    assert normalize_key("مـــدرسة", "ar") == normalize_key("مدرسه", "ar")
    assert normalize_key("على", "ar") == normalize_key("علي", "ar")

    # Latin : casefold + espaces
    assert normalize_key("  Théorème  ", "fr") == "théorème"


def test_ink_hash_tolerant_hamming():
    from app.domain.correction_layer import ink_hash, hamming, NEAR_THRESHOLD

    s_orig = _make_strokes(0.0, 0.0, jitter=0.0)
    # Légère variation d'écriture (~1px) et translation sur la page
    s_near = _make_strokes(100.0, 50.0, jitter=0.8)
    # Tracé complètement différent (vertical / diagonal inverse)
    s_diff = [
        Stroke(
            id="d1",
            points=[Point(x=10.0, y=10.0), Point(x=15.0, y=90.0), Point(x=90.0, y=10.0)],
            startTime=0.0,
            endTime=1.0,
        )
    ]

    h1 = ink_hash(s_orig)
    h2 = ink_hash(s_near)
    h3 = ink_hash(s_diff)

    assert hamming(h1, h2) <= NEAR_THRESHOLD
    assert hamming(h1, h3) > 0


def test_anti_poison_accepts_arabic_and_returns_readable_code():
    from app.domain.anti_poison import validate_correction, should_reject

    # En arabe, TrOCR sort du texte latin erroné ("o o o a") et l'utilisateur corrige en "مرحبا"
    assert should_reject("o o o a", "مرحبا", lang="ar", engine_supports_lang=False, confidence=0.3) is False
    ok, reason, code = validate_correction(
        predicted_text="o o o a",
        corrected_text="مرحبا",
        lang="ar",
        engine_supports_lang=False,
        confidence=0.3,
        return_code=True,
    )
    assert ok is True
    assert code == "OK"

    # En français avec haute confiance et moteur supporté, une réécriture totale reste bloquée avec code lisible
    ok2, reason2, code2 = validate_correction(
        predicted_text="les fonctions continues",
        corrected_text="tout a fait autre chose qui n a aucun rapport",
        lang="fr",
        engine_supports_lang=True,
        confidence=0.92,
        return_code=True,
    )
    assert ok2 is False
    assert code2 == "CORRECTION_TOO_FAR"


@pytest.mark.parametrize(
    "lang,pred_word,corr_word",
    [
        ("fr", "bijectiv", "bijective"),
        ("en", "theoreme", "theorem"),
        ("ar", "ooooa", "مرحبا"),
    ],
)
def test_feedback_then_recognize_returns_correction(lang, pred_word, corr_word):
    """
    Test d'acceptation 1.7 pour fr, en, ar :
    1) Reconnaissance initiale (mise en cache HTR du brut)
    2) Envoi d'une correction via POST /api/v1/ocr/feedback (même avec consent_train=False)
    3) Nouvelle reconnaissance des mêmes tracés -> renvoie le mot corrigé avec source='memory'
       (le cache HTR ne court-circuite plus la couche de correction)
    4) Vidage des caches mémoire -> survit grâce au repli et au dictionnaire
    5) Écriture différente produisant le même mot prédit -> corrigé dès la 1re fois (source='dictionary')
    """
    from app.ml.cache import htr_cache
    from app.domain.line_memory import line_memory

    htr_cache.clear()
    line_memory.clear()

    uid = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}
    strokes = _make_strokes()
    strokes_json = [
        {
            "id": s.id,
            "points": [{"x": p.x, "y": p.y} for p in s.points],
            "startTime": s.startTime,
            "endTime": s.endTime,
        }
        for s in strokes
    ]

    dummy_out = LineOut(
        text=pred_word,
        confidence=0.72,
        min_word_confidence=0.72,
        words=[WordOut(index=0, text=pred_word, confidence=0.72)],
        alternatives=[],
        engine="trocr_fr",
        model_version="v3",
    )
    fake_engine = MagicMock()
    fake_engine.version = "v3"
    fake_engine.recognize_lines.return_value = [dummy_out]

    # Mock de la session DB pour isoler le test unitaire tout en vérifiant la persistance
    stored_corrections = []
    stored_dict = {}

    class FakeQuery:
        def __init__(self, model):
            self.model = model

        def filter(self, *args, **kwargs):
            return self

        def filter_by(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def first(self):
            name = getattr(self.model, "__name__", "")
            if name == "OcrCorrection" and stored_corrections:
                return stored_corrections[-1]
            if name == "UserDictionary":
                return None
            return None

        def all(self):
            name = getattr(self.model, "__name__", "")
            if name == "OcrCorrection":
                return list(reversed(stored_corrections))
            if name == "UserDictionary":
                from types import SimpleNamespace
                return [
                    SimpleNamespace(wrong=k, right=v[0], count=v[1], language=lang)
                    for (l_k, k), v in stored_dict.items()
                    if l_k == lang
                ]
            return []

    fake_db = MagicMock()
    fake_db.query.side_effect = lambda m: FakeQuery(m)

    def _add(obj):
        name = obj.__class__.__name__
        if name == "OcrCorrection":
            if not getattr(obj, "id", None):
                obj.id = uuid.uuid4()
            stored_corrections.append(obj)
        elif name == "UserDictionary":
            stored_dict[(obj.language, obj.wrong)] = (obj.right, obj.count or 1)

    fake_db.add.side_effect = _add

    from app.db.session import get_db
    app.dependency_overrides[get_db] = lambda: fake_db
    client = TestClient(app)

    try:
        with patch("app.services.handwriting_service.registry.get", return_value=fake_engine), \
             patch("app.services.structural_htr_service.registry.get", return_value=fake_engine), \
             patch("app.db.session.SessionLocal", return_value=MagicMock(__enter__=lambda s: fake_db, __exit__=lambda *a: None)):

            # 1) Première reconnaissance -> résultat brut mis en cache
            r1 = client.post(
                "/api/v1/recognition",
                json={"strokes": strokes_json, "options": {"language": lang}},
                headers=headers,
            )
            assert r1.status_code == 200
            assert r1.json()["lines"][0]["text"] == pred_word

            # 2) Envoi du feedback (avec consent_train=False : la mémoire personnelle doit quand même marcher !)
            fb_resp = client.post(
                "/api/v1/ocr/feedback",
                json={
                    "scope": "word",
                    "word_index": 0,
                    "stroke_ids": ["s1", "s2"],
                    "strokes": strokes_json,
                    "language": lang,
                    "predicted_text": pred_word,
                    "corrected_text": corr_word,
                    "line_predicted": pred_word,
                    "line_corrected": corr_word,
                    "confidence": 0.72,
                    "consent_train": False,
                },
                headers=headers,
            )
            assert fb_resp.status_code == 200, fb_resp.text

            # 3) Relancer la reconnaissance sur les mêmes tracés :
            #    Malgré le cache HTR, la couche de correction s'applique en dernier -> source="memory"
            r2 = client.post(
                "/api/v1/recognition",
                json={"strokes": strokes_json, "options": {"language": lang}},
                headers=headers,
            )
            assert r2.status_code == 200
            line2 = r2.json()["lines"][0]
            assert line2["text"] == corr_word
            assert line2["source"] == "memory"

            # 3b) Vérifier aussi sur /api/v1/ocr/line-words et /api/v1/structural-htr
            r_lw = client.post(
                "/api/v1/ocr/line-words",
                json={"stroke_ids": ["s1", "s2"], "strokes": strokes_json, "language": lang},
                headers=headers,
            )
            assert r_lw.status_code == 200
            assert r_lw.json()["text"] == corr_word
            assert r_lw.json()["source"] == "memory"

            r_struct = client.post(
                "/api/v1/structural-htr",
                json={"strokes": strokes_json, "language": lang},
                headers=headers,
            )
            assert r_struct.status_code == 200
            assert r_struct.json()["elements"][0]["text"] == corr_word
            assert r_struct.json()["elements"][0]["source"] == "memory"

            # 4) Simuler un redémarrage backend (vidage des caches mémoire)
            line_memory.clear()
            htr_cache.clear()
            r3 = client.post(
                "/api/v1/recognition",
                json={"strokes": strokes_json, "options": {"language": lang}},
                headers=headers,
            )
            assert r3.status_code == 200
            assert r3.json()["lines"][0]["text"] == corr_word
            assert r3.json()["lines"][0]["source"] == "memory"

            # 5) Écriture complètement différente (autre forme géométrique) mais le modèle prédit `pred_word` :
            #    Le dictionnaire personnel doit corriger DÈS LA 1re CORRECTION -> source="dictionary"
            line_memory.clear()
            stored_corrections.clear()
            diff_strokes = [
                {
                    "id": "z1",
                    "points": [{"x": 10.0, "y": 10.0}, {"x": 20.0, "y": 95.0}, {"x": 95.0, "y": 15.0}],
                    "startTime": 0.0,
                    "endTime": 1.0,
                }
            ]
            r4 = client.post(
                "/api/v1/recognition",
                json={"strokes": diff_strokes, "options": {"language": lang}},
                headers=headers,
            )
            assert r4.status_code == 200
            line4 = r4.json()["lines"][0]
            assert line4["text"] == corr_word
            assert line4["source"] == "dictionary"
            assert line4["words"][0]["source"] == "dictionary"
    finally:
        app.dependency_overrides.clear()
