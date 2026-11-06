import pytest
from app.schemas.strokes import Stroke, Point
from app.ml.cache import line_cache_key, HtrCache


def make_stroke(s_id, points_data):
    return Stroke(
        id=s_id,
        points=[Point(x=p[0], y=p[1]) for p in points_data],
        startTime=0.0,
        endTime=1.0,
    )


def test_line_cache_key_identique():
    s1 = [make_stroke("s1", [(10, 10), (20, 20)])]
    s2 = [make_stroke("s1", [(10, 10), (20, 20)])]

    k1 = line_cache_key("u1", s1, engine="trocr", model_version="v2", render_cfg_hash="h1", num_beams=1, lang="fr")
    k2 = line_cache_key("u1", s2, engine="trocr", model_version="v2", render_cfg_hash="h1", num_beams=1, lang="fr")
    assert k1 == k2


def test_line_cache_key_miss_on_accent_or_dot():
    """Ajouter un point/accent (nouveau tracé) doit provoquer un cache miss."""
    s1 = [make_stroke("s1", [(10, 10), (20, 20)])]
    s2 = [
        make_stroke("s1", [(10, 10), (20, 20)]),
        make_stroke("s2_accent", [(15, 5), (16, 5)]),  # point ou accent ajouté
    ]

    k1 = line_cache_key("u1", s1, engine="trocr", model_version="v2", render_cfg_hash="h1", num_beams=1, lang="fr")
    k2 = line_cache_key("u1", s2, engine="trocr", model_version="v2", render_cfg_hash="h1", num_beams=1, lang="fr")
    assert k1 != k2


def test_line_cache_key_miss_on_model_version():
    """Changer la version du modèle doit invalider le cache."""
    s = [make_stroke("s1", [(10, 10), (20, 20)])]
    k_v2 = line_cache_key("u1", s, model_version="v2")
    k_v3 = line_cache_key("u1", s, model_version="v3")
    assert k_v2 != k_v3


def test_line_cache_key_miss_on_language():
    s = [make_stroke("s1", [(10, 10), (20, 20)])]
    k_fr = line_cache_key("u1", s, lang="fr")
    k_en = line_cache_key("u1", s, lang="en")
    assert k_fr != k_en


def test_htr_cache_lru():
    cache = HtrCache(max_memory_entries=2)
    cache.set("k1", {"text": "hello"})
    cache.set("k2", {"text": "world"})
    assert cache.get("k1") == {"text": "hello"}
    # Insertion de k3 doit évincer k2 (car k1 a été accédé récemment)
    cache.set("k3", {"text": "notely"})
    assert cache.get("k1") == {"text": "hello"}
    assert cache.get("k2") is None
    assert cache.get("k3") == {"text": "notely"}
