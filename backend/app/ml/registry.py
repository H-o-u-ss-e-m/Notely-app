"""
Registre des moteurs OCR avec chargement paresseux et politique LRU (ML-1 / §8.1).
Permet le routage actif par langue et l'éviction automatique des modèles excédentaires.
"""
import os
import yaml
import logging
import threading
from pathlib import Path
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional
from app.ml.engines.base import OcrEngine
from app.ml.engines.trocr import TrOCROcrEngine

logger = logging.getLogger("engine_registry")

DEFAULT_CONFIG_PATH = Path(__file__).parent / "models.yaml"


def build_engine(engine_name: str, engine_cfg: dict) -> OcrEngine:
    etype = engine_cfg.get("type", "trocr")
    source = engine_cfg.get("source", "microsoft/trocr-base-handwritten")
    version = engine_cfg.get("version", "v3")
    languages = tuple(engine_cfg.get("languages", ["en"]))

    if etype == "trocr":
        return TrOCROcrEngine(
            name=engine_name,
            model_name=source,
            languages=languages,
            version=version,
        )
    raise ValueError(f"Type de moteur inconnu : {etype}")


class EngineRegistry:
    def __init__(self, cfg: Optional[dict] = None, max_loaded: int = 2):
        if cfg is None:
            if DEFAULT_CONFIG_PATH.exists():
                with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
            else:
                cfg = {"engines": {}, "routing": {}, "thresholds": {"sure": 0.8, "wrong": 0.5}}
        self.cfg = cfg
        self.max_loaded = max_loaded
        self._loaded: OrderedDict[str, OcrEngine] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, engine_name: str) -> OcrEngine:
        with self._lock:
            if engine_name in self._loaded:
                self._loaded.move_to_end(engine_name)
                return self._loaded[engine_name]

            if engine_name not in self.cfg.get("engines", {}):
                raise KeyError(f"Moteur non configuré dans models.yaml : {engine_name}")

            # Évincer le plus ancien si limite atteinte
            while len(self._loaded) >= self.max_loaded:
                old_name, old_engine = self._loaded.popitem(last=False)
                logger.info(f"Éviction LRU du moteur {old_name}")
                old_engine.unload()

            eng = build_engine(engine_name, self.cfg["engines"][engine_name])
            self._loaded[engine_name] = eng
            return eng

    def chain_for(self, language: str) -> Tuple[List[str], float]:
        routing = self.cfg.get("routing", {})
        r = routing.get(language) or routing.get("en") or {"chain": ["trocr_en"], "min_confidence": 0.55}
        return r.get("chain", ["trocr_en"]), float(r.get("min_confidence", 0.55))

    def get_thresholds(self) -> Dict[str, float]:
        return self.cfg.get("thresholds", {"sure": 0.80, "wrong": 0.50})

    def loaded_count(self) -> int:
        with self._lock:
            return len(self._loaded)

    def clear(self) -> None:
        with self._lock:
            for eng in self._loaded.values():
                eng.unload()
            self._loaded.clear()


registry = EngineRegistry()
