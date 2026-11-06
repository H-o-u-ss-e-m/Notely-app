"""
Tests de non-régression pour le moteur OCR arabe et l'export PDF arabe (Mission 7).
"""
import pytest
from app.ml.registry import EngineRegistry
from app.services.pdf_generator_service import (
    pdf_generator_service,
    is_arabic_text,
    shape_arabic_for_pdf,
)
from app.schemas.structural import StructuralElement, PDFExportRequest


def test_arabic_engine_registered_and_inferred():
    registry = EngineRegistry()
    arabic_engine = registry.get("arabic_engine")
    assert arabic_engine.name == "arabic_engine"
    assert "ar" in arabic_engine.languages

    # Inférence factice avec image vierge
    from PIL import Image
    dummy_img = Image.new("RGB", (200, 50), color=(255, 255, 255))
    results = arabic_engine.recognize_lines([dummy_img])
    assert len(results) == 1
    assert results[0].confidence >= 0.80
    assert len(results[0].words) > 0


def test_arabic_text_detection_and_shaping():
    fr_text = "Cours de Mathématiques"
    ar_text = "مرحبا بكم في تطبيق نوتلي"

    assert not is_arabic_text(fr_text)
    assert is_arabic_text(ar_text)

    shaped = shape_arabic_for_pdf(ar_text)
    assert shaped != ""
    assert isinstance(shaped, str)


def test_arabic_pdf_generation_bytes():
    req = PDFExportRequest(
        subject="اللغة العربية",
        lessonTitle="الدرس الأول : الخط العربي",
        elements=[
            StructuralElement(id=1, bbox=[10.0, 20.0, 300.0, 50.0], type="h1", text="مقدمة في الخط العربي"),
            StructuralElement(id=2, bbox=[10.0, 60.0, 300.0, 100.0], type="paragraph", text="هذا نص تجريبي مكتوب باللغة العربية داخل تطبيق نوتلي."),
        ]
    )

    pdf_bytes = pdf_generator_service.generate_pdf_bytes(req)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
