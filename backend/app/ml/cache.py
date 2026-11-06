"""
Module de cache HTR (ML-12a / §8.12).
Clé basée sur le contenu exact des tracés, la configuration de rendu,
le modèle, la version, la langue et les hyperparamètres (fini le thumbnail 64x16).
Supporte un cache LRU en mémoire et Redis optionnel.
"""
import struct
import hashlib
import json
import logging
from collections import OrderedDict
from typing import Sequence, Optional, Any, Dict
from app.schemas.strokes import Stroke

logger = logging.getLogger("htr_cache")


def stroke_fingerprint(strokes: Sequence[Stroke]) -> str:
    """
    Calcule l'empreinte cryptographique des tracés manuscrits (indépendante de la config).
    Utilisée pour la mémoire de lignes exacte (§8.5.c) et le dédoublonnage.
    """
    h = hashlib.sha256()
    sorted_strokes = sorted(
        strokes,
        key=lambda s: (getattr(s, "startTime", 0.0), getattr(s, "id", "")),
    )
    for s in sorted_strokes:
        if getattr(s, "tool", "pen") == "eraser":
            continue
        points = getattr(s, "points", [])
        if points:
            coords = [v for p in points for v in (round(float(p.x), 1), round(float(p.y), 1))]
            h.update(struct.pack(f"<{len(coords)}f", *coords))
    return h.hexdigest()


def line_cache_key(
    user_id: str,
    strokes: Sequence[Stroke],
    *,
    engine: str = "trocr",
    model_version: str = "v2",
    render_cfg_hash: str = "default",
    num_beams: int = 1,
    lang: str = "fr",
) -> str:
    """
    Génère une clé d'empreinte SHA-256 cryptographiquement discriminante pour une ligne manuscrite.
    Ajouter un accent, un point ou changer l'ordre modifie la clé (cache miss).
    """
    h = hashlib.sha256()
    prefix = f"{user_id}|{engine}|{model_version}|{render_cfg_hash}|{num_beams}|{lang}"
    h.update(prefix.encode("utf-8"))

    # Trier les tracés pour stabilité (par startTime ou id)
    sorted_strokes = sorted(
        strokes,
        key=lambda s: (getattr(s, "startTime", 0.0), getattr(s, "id", "")),
    )

    for s in sorted_strokes:
        if getattr(s, "tool", "pen") == "eraser":
            continue
        s_id = str(getattr(s, "id", ""))
        h.update(s_id.encode("utf-8"))
        points = getattr(s, "points", [])
        if points:
            coords = [v for p in points for v in (round(float(p.x), 1), round(float(p.y), 1))]
            h.update(struct.pack(f"<{len(coords)}f", *coords))

    return h.hexdigest()


class HtrCache:
    """Cache à deux niveaux : mémoire LRU bornée + Redis optionnel."""

    def __init__(self, max_memory_entries: int = 1024, default_ttl_s: int = 86400):
        self.max_entries = max_memory_entries
        self.default_ttl_s = default_ttl_s
        self._memory_cache: OrderedDict[str, Any] = OrderedDict()
        self._redis_client = None
        self._redis_checked = False

    def _get_redis(self):
        if not self._redis_checked:
            self._redis_checked = True
            try:
                import redis
                from app.core.config import settings
                if hasattr(settings, "REDIS_URL") and settings.REDIS_URL:
                    r = redis.from_url(str(settings.REDIS_URL), decode_responses=True, socket_timeout=1.0)
                    r.ping()
                    self._redis_client = r
                    logger.info("HTR cache connecté à Redis avec succès.")
            except Exception as e:
                logger.debug(f"HTR cache : Redis non disponible ({e}), fallback mémoire LRU.")
                self._redis_client = None
        return self._redis_client

    def get(self, key: str) -> Optional[Any]:
        # 1. Vérifier mémoire locale
        if key in self._memory_cache:
            self._memory_cache.move_to_end(key)
            return self._memory_cache[key]

        # 2. Vérifier Redis si dispo
        r = self._get_redis()
        if r:
            try:
                val_str = r.get(f"htr:{key}")
                if val_str:
                    val = json.loads(val_str)
                    self._memory_cache[key] = val
                    if len(self._memory_cache) > self.max_entries:
                        self._memory_cache.popitem(last=False)
                    return val
            except Exception as e:
                logger.debug(f"Erreur lecture Redis HTR: {e}")

        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds or self.default_ttl_s

        # Sauvegarder en mémoire locale
        if key in self._memory_cache:
            self._memory_cache.move_to_end(key)
        self._memory_cache[key] = value

        if len(self._memory_cache) > self.max_entries:
            self._memory_cache.popitem(last=False)

        # Sauvegarder en Redis si dispo
        r = self._get_redis()
        if r:
            try:
                r.setex(f"htr:{key}", ttl, json.dumps(value, ensure_ascii=False))
            except Exception as e:
                logger.debug(f"Erreur écriture Redis HTR: {e}")

    def clear(self) -> None:
        self._memory_cache.clear()


htr_cache = HtrCache()
