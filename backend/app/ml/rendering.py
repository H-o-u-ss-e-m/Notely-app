"""
Module ML Rendering (ML-8).
Rendu configurable des tracés vectoriels en images lignes optimisées pour les moteurs OCR (TrOCR, etc.).
"""
from dataclasses import dataclass
import hashlib
import math
import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple, Optional, Sequence
from app.schemas.strokes import Stroke
from app.utils.geometry import estimate_slope
from app.utils.image_utils import rotate_cv_image_safe, pil_to_base64_url


@dataclass(frozen=True)
class RenderConfig:
    padding_factor: float = 0.25          # fraction de line_h ajoutée en padding vertical
    render_scale: int = 2                 # facteur de suréchantillonnage (1, 2, 3)
    stroke_rel_width: float = 0.06        # épaisseur = stroke_rel_width * H_med
    modulate_pressure: bool = False       # moduler l'épaisseur selon la pression du tracé
    deskew: bool = True                   # correction de pente (redressement horizontal)
    deskew_threshold_deg: float = 2.0     # angle minimal pour déclencher la rotation
    max_deskew_deg: float = 15.0          # angle maximal au-delà duquel la rotation est annulée (clamp)
    deslant: bool = False                 # cisaillement horizontal (redressement italique)
    min_aspect_pad: bool = True           # complète en blanc les lignes au ratio étroit (< 2:1)

    def hash(self) -> str:
        s = (
            f"{self.padding_factor}:{self.render_scale}:{self.stroke_rel_width}:"
            f"{self.modulate_pressure}:{self.deskew}:{self.deskew_threshold_deg}:"
            f"{self.max_deskew_deg}:{self.deslant}:{self.min_aspect_pad}"
        )
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


DEFAULT_RENDER_CONFIG = RenderConfig()


def estimate_line_angle(strokes: Sequence[Stroke]) -> float:
    """Estime l'angle moyen d'une ligne à partir de tous ses points."""
    xs: List[float] = []
    ys: List[float] = []
    for s in strokes:
        if getattr(s, "tool", "pen") == "eraser":
            continue
        for p in getattr(s, "points", []):
            xs.append(p.x)
            ys.append(p.y)
    return estimate_slope(xs, ys)


def compute_strokes_bbox(strokes: Sequence[Stroke]) -> List[float]:
    """Calcule [xMin, yMin, xMax, yMax] d'un groupe de tracés."""
    xs: List[float] = []
    ys: List[float] = []
    for s in strokes:
        if getattr(s, "tool", "pen") == "eraser":
            continue
        for p in getattr(s, "points", []):
            xs.append(p.x)
            ys.append(p.y)
    if not xs or not ys:
        return [0.0, 0.0, 100.0, 50.0]
    return [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]


def render_line(
    strokes: Sequence[Stroke],
    cfg: Optional[RenderConfig] = None,
    bbox: Optional[List[float]] = None,
    slanted_angle: Optional[float] = None,
    h_med: Optional[float] = None,
    include_base64: bool = False,
) -> Tuple[Image.Image, str]:
    """
    Rend une ligne de tracés en image PIL optimisée selon RenderConfig.
    
    Args:
        strokes: liste des tracés de la ligne
        cfg: configuration de rendu (défaut = RenderConfig())
        bbox: [xMin, yMin, xMax, yMax] pré-calculé ou calculé à la volée
        slanted_angle: angle de deskewing pré-calculé ou estimé à la volée
        h_med: hauteur médiane des tracés (pour normaliser l'épaisseur)
        include_base64: générer l'URL base64 (WebP ou PNG)
    
    Returns:
        (PIL.Image RGB, base64_str)
    """
    if cfg is None:
        cfg = DEFAULT_RENDER_CONFIG

    if bbox is None:
        bbox = compute_strokes_bbox(strokes)

    x_min, y_min, x_max, y_max = bbox
    line_w = max(x_max - x_min, 10.0)
    line_h = max(y_max - y_min, 10.0)

    # 1. Marges (padding)
    padding_y = max(int(line_h * cfg.padding_factor), 15)
    padding_x = max(int(line_w * 0.05), 20)

    crop_x1 = max(0, int(x_min - padding_x))
    crop_y1 = max(0, int(y_min - padding_y))
    crop_x2 = int(x_max + padding_x)
    crop_y2 = int(y_max + padding_y)

    crop_w = max(crop_x2 - crop_x1, 20)
    crop_h = max(crop_y2 - crop_y1, 20)

    scale = cfg.render_scale
    scaled_w = int(crop_w * scale)
    scaled_h = int(crop_h * scale)

    # Canvas fond blanc
    img_bgr = np.ones((scaled_h, scaled_w, 3), dtype=np.uint8) * 255

    # 2. Dessin des tracés
    for stroke in strokes:
        if getattr(stroke, "tool", "pen") == "eraser" or len(stroke.points) < 2:
            continue

        color_bgr = (0, 0, 0)

        # Calcul épaisseur
        if h_med and h_med > 0:
            base_thickness = max(int(h_med * cfg.stroke_rel_width * scale), 2)
        else:
            raw_w = getattr(stroke, "width", 3.0) or 3.0
            base_thickness = max(int(raw_w * scale), 2)

        pts = [
            (
                int((p.x - crop_x1) * scale),
                int((p.y - crop_y1) * scale),
            )
            for p in stroke.points
        ]

        pressures = [getattr(p, "pressure", 0.5) or 0.5 for p in stroke.points]

        for i in range(len(pts) - 1):
            if cfg.modulate_pressure:
                seg_press = (pressures[i] + pressures[i + 1]) / 2.0
                thick = max(int(base_thickness * (0.6 + 0.8 * seg_press)), 1)
            else:
                thick = base_thickness

            cv2.line(
                img_bgr, pts[i], pts[i + 1],
                color_bgr, thick,
                lineType=cv2.LINE_AA,
            )

    # 3. Deskewing avec clamp strict (§8.8)
    angle = 0.0
    if cfg.deskew:
        if slanted_angle is None:
            angle = estimate_line_angle(strokes)
        else:
            angle = float(slanted_angle)

        if abs(angle) < cfg.deskew_threshold_deg or abs(angle) > cfg.max_deskew_deg:
            angle = 0.0

        if abs(angle) >= cfg.deskew_threshold_deg:
            img_bgr = rotate_cv_image_safe(img_bgr, -angle)

    # 4. Deslant (optionnel)
    if cfg.deslant:
        # Cisaillement horizontal léger (-10°)
        shear = 0.15
        h, w = img_bgr.shape[:2]
        M = np.float32([[1, shear, -shear * h / 2], [0, 1, 0]])
        img_bgr = cv2.warpAffine(
            img_bgr, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )

    # 5. Aspect ratio padding (évite les fragments ultra hauts et étroits)
    if cfg.min_aspect_pad:
        h, w = img_bgr.shape[:2]
        if w / max(h, 1) < 2.0:
            target_w = int(h * 2.0)
            pad_left = (target_w - w) // 2
            pad_right = target_w - w - pad_left
            img_bgr = cv2.copyMakeBorder(
                img_bgr, 0, 0, pad_left, pad_right,
                cv2.BORDER_CONSTANT, value=(255, 255, 255)
            )

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    b64_str = pil_to_base64_url(pil_img) if include_base64 else ""

    return pil_img, b64_str
