"""
Mémoire de lignes exacte et tolérante (ML-5 / §8.5.c & Plan v2 §1.3, §1.4).
Si un utilisateur a déjà corrigé une ligne et réexécute l'OCR sur les mêmes tracés
(ou une réécriture très proche avec distance de Hamming <= NEAR_THRESHOLD sur ink_hash 32x8),
la correction validée est réappliquée directement.

Architecture à 3 niveaux :
1. Mémoire LRU de processus (ultra-rapide, 10 000 entrées + index ink_hash par utilisateur)
2. Redis partagé multi-workers (TTL 90 jours = 7 776 000 s)
3. Persistance durable en base de données dans `ocr_corrections` (source de vérité),
   garantissant la survie des corrections après redémarrage du serveur.
"""
import os
import logging
import threading
from collections import OrderedDict, defaultdict
from typing import Optional, List, Tuple

from app.domain.correction_layer import hamming, NEAR_THRESHOLD

logger = logging.getLogger("line_memory")

TTL_90_DAYS = 90 * 86400  # 90 jours en secondes (§8.5.c)


class LineMemory:
    """
    Gestionnaire de la mémoire de lignes (exacte + tolérante ink_hash) avec repli durable sur ocr_corrections.
    """
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self._entries: OrderedDict[str, str] = OrderedDict()
        # Index mémoire par utilisateur pour recherche par distance de Hamming : user_id -> [(ink_hash_hex, text, lang)]
        self._ink_entries: dict[str, List[Tuple[str, str, str]]] = defaultdict(list)
        self._lock = threading.Lock()
        self._redis_client = None
        self._redis_checked = False

    def _get_redis(self):
        if os.getenv("ENV") in ("test", "ci"):
            return None
        if not self._redis_checked:
            self._redis_checked = True
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                import redis
                client = redis.Redis.from_url(
                    redis_url,
                    socket_timeout=0.1,
                    socket_connect_timeout=0.1,
                    decode_responses=True,
                )
                client.ping()
                self._redis_client = client
                logger.info("Redis connecté pour la mémoire de lignes (TTL 90 j).")
            except Exception:
                self._redis_client = None
        return self._redis_client

    def _make_key(self, user_id: str, stroke_fingerprint: str) -> str:
        return f"line_mem:{user_id}:{stroke_fingerprint}"

    def store(
        self,
        user_id: str,
        stroke_fingerprint: str,
        line_corrected: str,
        ink_hash_val: Optional[str] = None,
        lang: str = "fr",
    ) -> None:
        if not user_id or not line_corrected:
            return

        with self._lock:
            if stroke_fingerprint:
                key = self._make_key(user_id, stroke_fingerprint)
                if key in self._entries:
                    self._entries.move_to_end(key)
                self._entries[key] = line_corrected
                if len(self._entries) > self.max_entries:
                    self._entries.popitem(last=False)

            if ink_hash_val:
                u_list = self._ink_entries[str(user_id)]
                # Éviter les doublons exacts de ink_hash
                u_list = [(ih, txt, lg) for (ih, txt, lg) in u_list if ih != ink_hash_val]
                u_list.append((ink_hash_val, line_corrected, (lang or "fr").lower()))
                if len(u_list) > 500:
                    u_list = u_list[-500:]
                self._ink_entries[str(user_id)] = u_list

        # 2. Mise en cache Redis si actif
        if stroke_fingerprint:
            r = self._get_redis()
            if r:
                try:
                    r.setex(self._make_key(user_id, stroke_fingerprint), TTL_90_DAYS, line_corrected)
                except Exception as e:
                    logger.debug(f"Erreur d'écriture Redis line_memory : {e}")

    def lookup(
        self,
        user_id: str,
        stroke_fingerprint: str = "",
        ink_hash_val: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> Optional[str]:
        if not user_id:
            return None

        # ── A. Recherche exacte par stroke_fingerprint ─────────────────────────
        if stroke_fingerprint:
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
                        with self._lock:
                            self._entries[key] = val
                        return val
                except Exception:
                    pass

            # 3. Repli durable sur PostgreSQL `ocr_corrections` (exact)
            try:
                import uuid
                from app.db.session import SessionLocal
                from app.db.models.ocr_correction import OcrCorrection

                u_uuid = uuid.UUID(str(user_id))
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
                    if corr and getattr(corr, "stroke_fingerprint", None) in (None, stroke_fingerprint):
                        text = getattr(corr, "line_corrected", None) or getattr(corr, "corrected_text", None)
                        if text:
                            self.store(
                                str(user_id),
                                stroke_fingerprint,
                                text,
                                ink_hash_val=getattr(corr, "ink_hash", None),
                                lang=getattr(corr, "language", lang or "fr"),
                            )
                            return text
            except Exception:
                pass

        # ── B. Recherche tolérante par ink_hash (distance de Hamming <= NEAR_THRESHOLD) ─
        if ink_hash_val and ink_hash_val != ("0" * 64):
            best_text: Optional[str] = None
            best_dist: int = NEAR_THRESHOLD + 1

            # 1. Recherche dans l'index mémoire local de l'utilisateur
            with self._lock:
                candidates = list(self._ink_entries.get(str(user_id), []))
            for cand_ih, cand_txt, cand_lang in reversed(candidates):
                if lang and cand_lang and cand_lang != lang.lower():
                    continue
                d = hamming(ink_hash_val, cand_ih)
                if d < best_dist:
                    best_dist = d
                    best_text = cand_txt
                    if d == 0:
                        break

            if best_text is not None and best_dist <= NEAR_THRESHOLD:
                return best_text

            # 2. Recherche dans les corrections récentes de l'utilisateur en base
            try:
                import uuid
                from app.db.session import SessionLocal
                from app.db.models.ocr_correction import OcrCorrection

                u_uuid = uuid.UUID(str(user_id))
                with SessionLocal() as db:
                    recent = (
                        db.query(OcrCorrection)
                        .filter(OcrCorrection.user_id == u_uuid)
                        .order_by(OcrCorrection.created_at.desc())
                        .limit(200)
                        .all()
                    )
                    for corr in recent:
                        c_ih = getattr(corr, "ink_hash", None)
                        if not c_ih:
                            continue
                        c_lang = getattr(corr, "language", None)
                        if lang and c_lang and c_lang.lower() != lang.lower():
                            continue
                        d = hamming(ink_hash_val, c_ih)
                        if d < best_dist:
                            txt = getattr(corr, "line_corrected", None) or getattr(corr, "corrected_text", None)
                            if txt:
                                best_dist = d
                                best_text = txt
                    if best_text is not None and best_dist <= NEAR_THRESHOLD:
                        self.store(str(user_id), stroke_fingerprint, best_text, ink_hash_val=ink_hash_val, lang=lang or "fr")
                        return best_text
            except Exception:
                pass

        return None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._ink_entries.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._entries)


line_memory = LineMemory()
