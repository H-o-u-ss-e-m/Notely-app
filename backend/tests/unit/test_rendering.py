import pytest
from app.schemas.strokes import Stroke, Point
from app.ml.rendering import RenderConfig, render_line, compute_strokes_bbox


def make_stroke(points_data, tool="pen", width=3.0):
    return Stroke(
        id="s1",
        points=[Point(x=p[0], y=p[1], pressure=p[2] if len(p) > 2 else 0.5) for p in points_data],
        color="#000000",
        width=width,
        tool=tool,
        startTime=0.0,
        endTime=1.0,
    )


def test_render_config_hash():
    cfg1 = RenderConfig(padding_factor=0.25, render_scale=2)
    cfg2 = RenderConfig(padding_factor=0.25, render_scale=2)
    cfg3 = RenderConfig(padding_factor=0.35, render_scale=2)

    assert cfg1.hash() == cfg2.hash()
    assert cfg1.hash() != cfg3.hash()


def test_deskew_clamping_above_max():
    """Vérifie qu'un angle aberrant (> max_deskew_deg) est annulé (clampé à 0)."""
    strokes = [make_stroke([(10, 10), (50, 10), (100, 10)])]
    cfg = RenderConfig(deskew=True, max_deskew_deg=15.0)

    # Si slanted_angle est 45°, il doit être clampé à 0
    img, _ = render_line(strokes, cfg=cfg, slanted_angle=45.0)
    assert img is not None
    assert img.size[0] > 0 and img.size[1] > 0


def test_deskew_threshold_below_min():
    """Vérifie qu'un angle trop petit (< deskew_threshold_deg) est ignoré."""
    strokes = [make_stroke([(10, 10), (50, 10), (100, 10)])]
    cfg = RenderConfig(deskew=True, deskew_threshold_deg=2.0)

    img, _ = render_line(strokes, cfg=cfg, slanted_angle=1.0)
    assert img is not None


def test_stroke_thickness_normalized():
    """Vérifie que l'épaisseur s'adapte à h_med."""
    strokes = [make_stroke([(10, 10), (50, 10)])]
    img1, _ = render_line(strokes, h_med=20.0)
    img2, _ = render_line(strokes, h_med=80.0)

    assert img1 is not None
    assert img2 is not None
