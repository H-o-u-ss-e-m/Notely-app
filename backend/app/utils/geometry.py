import math
import numpy as np
from typing import List, Dict

def calculate_stroke_bbox(points: List[Dict[str, float]]) -> Dict[str, float]:
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    return {
        "xMin": float(min(xs)),
        "yMin": float(min(ys)),
        "xMax": float(max(xs)),
        "yMax": float(max(ys))
    }

def estimate_slope(x_coords: List[float], y_coords: List[float]) -> float:
    if len(x_coords) < 2:
        return 0.0
    dx = max(x_coords) - min(x_coords)
    if dx < 30.0:
        return 0.0
    try:
        slope, _ = np.polyfit(x_coords, y_coords, 1)
        angle_rad = math.atan(slope)
        return float(math.degrees(angle_rad))
    except Exception:
        return 0.0
