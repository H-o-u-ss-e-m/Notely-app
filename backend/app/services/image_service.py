"""
ImageService v2 — Façade de rendu vectoriel (délègue à app.ml.rendering.render_line).
Assure la rétrocompatibilité complète avec render_line_crop.
"""
import logging
from PIL import Image
from typing import List, Tuple, Optional
from app.schemas.strokes import Stroke
from app.core.config import settings
from app.ml.rendering import render_line, RenderConfig

logger = logging.getLogger("image_service")


class ImageService:

    @staticmethod
    def render_line_crop(
        strokes: List[Stroke],
        bbox: List[float],
        slanted_angle: float = 0.0,
        canvas_width: float = 1200.0,
        canvas_height: float = 800.0,
        render_scale: float = 2.0,
        include_base64: bool = True,
        h_med: Optional[float] = None,
    ) -> Tuple[Image.Image, str]:
        """
        Rend les tracés d'une ligne en image PIL (fond blanc, texte noir).
        Délègue à app.ml.rendering.render_line avec RenderConfig configuré.
        """
        cfg = RenderConfig(
            padding_factor=getattr(settings, "PADDING_FACTOR", 0.25),
            render_scale=int(render_scale),
            stroke_rel_width=0.06,
            deskew=True,
            deskew_threshold_deg=getattr(settings, "DESKEW_THRESHOLD_DEG", 2.0),
            max_deskew_deg=getattr(settings, "MAX_DESKEW_DEG", 15.0),
            deslant=False,
            min_aspect_pad=True,
        )

        return render_line(
            strokes=strokes,
            cfg=cfg,
            bbox=bbox,
            slanted_angle=slanted_angle,
            h_med=h_med,
            include_base64=include_base64,
        )


image_service = ImageService()
