"""
Mémoire de lignes exacte (ML-5 / §8.5.c).
Si un utilisateur a déjà corrigé une ligne et réexécute l'OCR sur les mêmes tracés,
la correction validée est réappliquée directement sans réinvoquer le modèle.

Architecture à 3 niveaux :
1. Mémoire LRU de processus (ultra-rapide, 10 000 entrées)
2. Redis partagé multi-workers (TTL 90 jours = 7 776 000 s)
3. Persistance durable en base de données dans `ocr_corrections` (source de vérité),
   garantissant la survie des corrections après redémarrage du serveur.
"""
import os
import logging
import threading
from collections import OrderedDict
from typing import Optional, Dict

logger = logging.getLogger("line_memory")

TTL_90_DAYS = 90 * 86400  # 90 jours en secondes (§8.5.c)


class LineMemory:
    """
    Gestionnaire de la mémoire de lignes exacte avec repli durable sur ocr_corrections.
    """
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self._entries: OrderedDict[str, str] = OrderedDict()
        self._lock = threading.Lock()
        self._redis_client = None
        self._redis_checked = False

    def _get_redis(self):
        if not self._redis_checked:
            self._redis_checked = True
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                import redis
                client = redis.Redis.from_url(redis_url, socket_timeout=0.2, decode_responses=True)
                client.ping()
                self._redis_client = client
                logger.info("Redis connecté pour la mémoire de lignes (TTL 90 j).")
            except Exception:
                self._redis_client = None
        return self._redis_client

    def _make_key(self, user_id: str, stroke_fingerprint: str) -> str:
        return f"line_mem:{user_id}:{stroke_fingerprint}"

    def store(self, user_id: str, stroke_fingerprint: str, line_corrected: str) -> None:
        if not user_id or not stroke_fingerprint or not line_corrected:
            return
        key = self._make_key(user_id, stroke_fingerprint)

        # 1. Mise en cache mémoire locale
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
            self._entries[key] = line_corrected
            if len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

        # 2. Mise en cache Redis si actif
        r = self._get_redis()
        if r:
            try:
                r.setex(key, TTL_90_DAYS, line_corrected)
            except Exception as e:
                logger.debug(f"Erreur d'écriture Redis line_memory : {e}")

    def lookup(self, user_id: str, stroke_fingerprint: str) -> Optional[str]:
        if not user_id or not stroke_fingerprint:
            return None
        key = self._make_key(user_id, stroke_fingerprint)

        # 1. Vérification dans la mémoire LRU locale
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
                return self._entries[key]

        # 2. Vérification dans Redis si actif
        r = self._get_redis()
        if r:
            try:
                val = r.get(key)
                if val:
                    # Enregistrer dans le cache mémoire local
                    with self._lock:
                        self._entries[key] = val
                    return val
            except Exception:
                pass

        # 3. Repli durable sur PostgreSQL `ocr_corrections` (source de vérité au redémarrage)
        try:
            import uuid
            from app.db.session import SessionLocal
            from app.db.models.ocr_correction import OcrCorrection

            u_uuid = uuid.UUID(user_id)
            with SessionLocal() as db:
                corr = (
                    db.query(OcrCorrection)
                    .filter(
                        OcrCorrection.user_id == u_uuid,
                        OcrCorrection.stroke_fingerprint == stroke_fingerprint,
                    )
                    .order_by(OcrCorrection.created_at.desc())
                    .first()
                )
                if corr and (corr.line_corrected or corr.corrected_text):
                    text = corr.line_corrected or corr.corrected_text
                    # Réinjecter en mémoire
                    self.store(user_id, stroke_fingerprint, text)
                    return text
        except Exception:
            pass

        return None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._entries)


line_memory = LineMemory()
