import pytest
from app.ml.registry import EngineRegistry, build_engine


def test_registry_chain_for_languages():
    cfg = {
        "engines": {
            "trocr_fr": {"type": "trocr", "source": "dummy", "languages": ["fr"], "version": "v3"},
            "trocr_en": {"type": "trocr", "source": "dummy", "languages": ["en"], "version": "v3"},
        },
        "routing": {
            "fr": {"chain": ["trocr_fr"], "min_confidence": 0.55},
            "en": {"chain": ["trocr_en"], "min_confidence": 0.55},
        },
        "thresholds": {"sure": 0.80, "wrong": 0.50},
    }

    reg = EngineRegistry(cfg=cfg, max_loaded=2)

    chain_fr, min_c_fr = reg.chain_for("fr")
    assert chain_fr == ["trocr_fr"]
    assert min_c_fr == 0.55

    chain_en, min_c_en = reg.chain_for("en")
    assert chain_en == ["trocr_en"]

    # Fallback sur en pour langue inconnue
    chain_unk, _ = reg.chain_for("unknown")
    assert chain_unk == ["trocr_en"]


def test_registry_lru_eviction():
    cfg = {
        "engines": {
            "m1": {"type": "trocr", "source": "microsoft/trocr-base-handwritten", "languages": ["fr"], "version": "v1"},
            "m2": {"type": "trocr", "source": "microsoft/trocr-base-handwritten", "languages": ["en"], "version": "v1"},
            "m3": {"type": "trocr", "source": "microsoft/trocr-base-handwritten", "languages": ["de"], "version": "v1"},
        },
        "routing": {},
        "thresholds": {"sure": 0.80, "wrong": 0.50},
    }

    reg = EngineRegistry(cfg=cfg, max_loaded=2)

    # Création mockée pour tester la politique LRU sans charger 3 modèles HuggingFace
    class FakeEngine:
        def __init__(self, name):
            self.name = name
            self.unloaded = False
        def unload(self):
            self.unloaded = True

    f1 = FakeEngine("m1")
    f2 = FakeEngine("m2")
    f3 = FakeEngine("m3")

    with reg._lock:
        reg._loaded["m1"] = f1
        reg._loaded["m2"] = f2

    assert reg.loaded_count() == 2

    # L'accès à m1 le rend le plus récent
    with reg._lock:
        reg._loaded.move_to_end("m1")

    # Insertion d'un 3ème élément : m2 doit être évincé car m1 a été touché
    with reg._lock:
        while len(reg._loaded) >= reg.max_loaded:
            old_name, old_eng = reg._loaded.popitem(last=False)
            old_eng.unload()
        reg._loaded["m3"] = f3

    assert f2.unloaded is True
    assert f1.unloaded is False
    assert "m2" not in reg._loaded
    assert "m1" in reg._loaded
    assert "m3" in reg._loaded
