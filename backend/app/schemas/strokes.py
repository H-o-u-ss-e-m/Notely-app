from typing import List, Optional
from pydantic import BaseModel, Field
from app.core.limits import MAX_POINTS_PER_STROKE, MAX_TOTAL_POINTS, MAX_ID_LEN

class Point(BaseModel):
    x: float = Field(ge=-10_000, le=10_000)
    y: float = Field(ge=-10_000, le=10_000)
    timestamp: Optional[float] = None
    pressure: Optional[float] = 1.0

class BoundingBox(BaseModel):
    xMin: float
    yMin: float
    xMax: float
    yMax: float

def check_total_points(strokes) -> None:
    """Raise ValueError if total point count exceeds the limit (-> 422)."""
    if sum(len(s.points) for s in strokes) > MAX_TOTAL_POINTS:
        raise ValueError(f"Trop de points au total (max {MAX_TOTAL_POINTS})")


class Stroke(BaseModel):
    id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    points: List[Point] = Field(max_length=MAX_POINTS_PER_STROKE)
    startTime: float
    endTime: float
    color: Optional[str] = "#000000"
    width: Optional[float] = 3.0
    tool: Optional[str] = "pen"
    contentType: Optional[str] = "normal"  # normal | h1 | h2 | h3 | h4 | h5 | h6
    pointerType: Optional[str] = "pen"  # mouse | touch | pen
    bbox: Optional[BoundingBox] = None

    def calculate_bbox(self) -> BoundingBox:
        if self.bbox is not None:
            return self.bbox
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return BoundingBox(xMin=min(xs), yMin=min(ys), xMax=max(xs), yMax=max(ys))
