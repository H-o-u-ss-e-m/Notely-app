import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.recognition import router as recognition_router
from app.core.security import create_access_token
from app.ml.engines.base import LineOut, WordOut

app = FastAPI()
app.include_router(recognition_router, prefix="/api/v1")

client = TestClient(app)


def _headers():
    return {"Authorization": f"Bearer {create_access_token({'sub': 'test-user'})}"}


def test_line_words_endpoint():
    dummy_line_out = LineOut(
        text="dérivables continues",
        confidence=0.88,
        min_word_confidence=0.85,
        words=[
            WordOut(index=0, text="dérivables", confidence=0.85, alternatives=["derivables"]),
            WordOut(index=1, text="continues", confidence=0.91, alternatives=[]),
        ],
        alternatives=["derivables continues"],
        engine="trocr_fr",
        model_version="v3",
    )

    fake_engine = MagicMock()
    fake_engine.version = "v3"
    fake_engine.recognize_lines.return_value = [dummy_line_out]

    with patch("app.services.handwriting_service.registry.get", return_value=fake_engine):
        payload = {
            "stroke_ids": ["s1"],
            "strokes": [
                {
                    "id": "s1",
                    "points": [{"x": 10.0, "y": 10.0}, {"x": 50.0, "y": 10.0}],
                    "startTime": 0.0,
                    "endTime": 1.0,
                }
            ],
            "language": "fr",
            "num_beams": 1,
            "include_thumbnail": True,
        }

        response = client.post("/api/v1/ocr/line-words", json=payload, headers=_headers())
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["text"] == "dérivables continues"
        assert len(data["words"]) == 2
        assert data["words"][0]["text"] == "dérivables"
        assert data["words"][0]["confidence"] == 0.85
        assert data["confidence"] == 0.88
        assert data["min_word_confidence"] == 0.85
        assert "alternatives" in data
        assert "thumbnail" in data


def test_recognition_endpoint_with_words():
    dummy_line_out = LineOut(
        text="bonjour le monde",
        confidence=0.92,
        min_word_confidence=0.89,
        words=[
            WordOut(index=0, text="bonjour", confidence=0.95),
            WordOut(index=1, text="le", confidence=0.92),
            WordOut(index=2, text="monde", confidence=0.89),
        ],
        engine="trocr_fr",
        model_version="v3",
    )

    fake_engine = MagicMock()
    fake_engine.version = "v3"
    fake_engine.recognize_lines.return_value = [dummy_line_out]

    with patch("app.services.handwriting_service.registry.get", return_value=fake_engine):
        payload = {
            "strokes": [
                {
                    "id": "s1",
                    "points": [{"x": 10.0, "y": 10.0}, {"x": 50.0, "y": 10.0}],
                    "startTime": 0.0,
                    "endTime": 1.0,
                }
            ],
            "options": {
                "language": "fr",
                "debug": False,
                "with_words": True,
            },
        }

        response = client.post("/api/v1/recognition", json=payload, headers=_headers())
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert len(data["lines"]) == 1
        line = data["lines"][0]
        assert line["text"] == "bonjour le monde"
        assert len(line["words"]) == 3
        assert line["words"][0]["text"] == "bonjour"
        assert line["confidence"] == 0.92
