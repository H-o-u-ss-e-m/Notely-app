"""Test de segmentation unitaire moderne (remplace l'ancien fichier racine obsolete)."""
import time
import pytest
from app.schemas.strokes import Stroke, Point, BoundingBox
from app.services.segmentation_service import segmentation_service


def create_stroke(stroke_id: str, x: float, y: float, num_pts: int = 5, dx: float = 10.0, dy: float = 0.0):
    pts = []
    now = time.time()
    for i in range(num_pts):
        pts.append(Point(x=x + i * dx, y=y + i * dy, timestamp=now + i * 0.01, pressure=1.0))
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    b = BoundingBox(xMin=min(xs), yMin=min(ys), xMax=max(xs), yMax=max(ys))
    return Stroke(
        id=stroke_id,
        points=pts,
        startTime=now,
        endTime=now + num_pts * 0.01,
        color="#000000",
        width=3.0,
        tool="pen",
        pointerType="pen",
        bbox=b,
    )


def test_empty_segmentation():
    lines = segmentation_service.segment_strokes([])
    assert lines == []


def test_single_stroke():
    s = create_stroke("s1", 10, 20)
    lines = segmentation_service.segment_strokes([s])
    assert len(lines) == 1
    assert lines[0]["stroke_ids"] == ["s1"]


def test_horizontal_line_clustering():
    s1 = create_stroke("s1", 10, 20)
    s2 = create_stroke("s2", 70, 22)
    s3 = create_stroke("s3", 10, 100)  # Deuxieme ligne plus bas

    lines = segmentation_service.segment_strokes([s1, s2, s3])
    assert len(lines) == 2
    assert set(lines[0]["stroke_ids"]) == {"s1", "s2"}
    assert lines[1]["stroke_ids"] == ["s3"]
