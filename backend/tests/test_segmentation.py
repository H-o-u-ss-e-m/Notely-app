import time
import pytest
from app.schemas.strokes import Stroke, Point, BoundingBox
from app.services.segmentation_service import segmentation_service

def create_stroke(stroke_id: str, x: float, y: float, num_pts: int = 5, dx: float = 10.0, dy: float = 0.0):
    pts = []
    now = time.time()
    for i in range(num_pts):
        pts.append(Point(x=x + i*dx, y=y + i*dy, timestamp=now + i*0.01, pressure=1.0))
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    b = BoundingBox(xMin=min(xs), yMin=min(ys), xMax=max(xs), yMax=max(ys))
    return Stroke(
        id=stroke_id,
        points=pts,
        startTime=now,
        endTime=now + num_pts*0.01,
        color="#000000",
        width=3.0,
        tool="pen",
        pointerType="pen",
        bbox=b
    )

def test_segmentation_single_line():
    s1 = create_stroke("s1", 100, 100)
    s2 = create_stroke("s2", 200, 102)
    groups = segmentation_service.segment_strokes([s1, s2])
    assert len(groups) == 1
    assert groups[0]["id"] == 1
    assert len(groups[0]["stroke_ids"]) == 2

def test_segmentation_multi_line():
    s1 = create_stroke("s1", 100, 100)
    s2 = create_stroke("s2", 100, 250)
    s3 = create_stroke("s3", 100, 400)
    groups = segmentation_service.segment_strokes([s1, s2, s3])
    assert len(groups) == 3
    assert groups[0]["id"] == 1
    assert groups[1]["id"] == 2
    assert groups[2]["id"] == 3
