"""
Couche de correction finale (Partie 1 — NOTELY Plan d'amélioration v2).
Principes :
1. Le cache HTR ne stocke que le résultat brut / post-traité linguistiquement.
2. CorrectionLayer est TOUJOURS appliquée EN DERNIER à chaque requête, hors cache.
3. Supporte :
   - Normalisation arabe (tashkeel, tatweel, variantes d'alef, ى/ي, ة/ه) et latine (casefold).
   - Hash visuel tolérant `ink_hash` (grille 32x8 = 256 bits, distance de Hamming <= 12).
   - Mémoire de ligne L0 (hash exact puis hash visuel tolérant) -> source = "memory".
   - Dictionnaire personnel L1 appliqué dès la 1re correction -> source = "dictionary".
"""
import re
import unicodedata
import numpy as np
from typing import Any, List, Optional, Sequence

_AR_MARKS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640\u200e\u200f]")
_AR_CHARS = re.compile(r"[\u0600-\u06FF]")

NEAR_THRESHOLD: int = 12  # ~5% de 256 bits


def normalize_key(text: str, lang: str = "fr") -> str:
    """
    Clé de COMPARAISON uniquement. Le texte rendu à l'utilisateur reste exact.
    Pour l'arabe : retire tashkeel, tatweel, marques bidi, unifie alef (إأآٱ -> ا), ى->ي, ة->ه.
    Pour les autres langues : casefold().
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text).strip()
    is_ar = (lang or "").lower().startswith("ar") or bool(_AR_CHARS.search(t))
    if is_ar:
        t = _AR_MARKS.sub("", t)
        t = re.sub(r"[إأآٱ]", "ا", t)
        t = t.replace("ى", "ي").replace("ة", "ه")
    else:
        t = t.casefold()
    return re.sub(r"\s+", " ", t).strip()


def _extract_stroke_points(stroke: Any) -> Optional[np.ndarray]:
    """Extrait les coordonnées [[x, y], ...] d'un Stroke (objet Pydantic ou dict)."""
    tool = getattr(stroke, "tool", None) if not isinstance(stroke, dict) else stroke.get("tool", "pen")
    if tool == "eraser":
        return None
    pts_raw = getattr(stroke, "points", None) if not isinstance(stroke, dict) else stroke.get("points", [])
    if not pts_raw:
        return None
    coords = []
    for p in pts_raw:
        if isinstance(p, dict):
            coords.append([float(p.get("x", 0.0)), float(p.get("y", 0.0))])
        elif hasattr(p, "x") and hasattr(p, "y"):
            coords.append([float(p.x), float(p.y)])
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            coords.append([float(p[0]), float(p[1])])
    if not coords:
        return None
    return np.asarray(coords, dtype=float)


def ink_hash(strokes: Sequence[Any], w: int = 32, h: int = 8) -> int:
    """
    Calcule une empreinte visuelle tolérante de 256 bits en rastérisant la ligne
    normalisée dans une grille binaire 32x8.
    """
    if not strokes:
        return 0
    stroke_arrays = []
    for s in strokes:
        arr = _extract_stroke_points(s)
        if arr is not None and len(arr) > 0:
            stroke_arrays.append(arr)
    if not stroke_arrays:
        return 0

    pts = np.concatenate(stroke_arrays, axis=0)
    mn = pts.min(axis=0)
    span = np.maximum(pts.max(axis=0) - mn, 1.0)
    grid = np.zeros((h, w), dtype=np.uint8)

    for arr in stroke_arrays:
        p = (arr - mn) / span
        if len(p) == 1:
            q = p[0]
            r_idx = min(max(int(q[1] * (h - 1) + 0.5), 0), h - 1)
            c_idx = min(max(int(q[0] * (w - 1) + 0.5), 0), w - 1)
            grid[r_idx, c_idx] = 1
        else:
            for a, b in zip(p[:-1], p[1:]):
                for t in np.linspace(0.0, 1.0, 8):
                    q = a + (b - a) * t
                    r_idx = min(max(int(q[1] * (h - 1) + 0.5), 0), h - 1)
                    c_idx = min(max(int(q[0] * (w - 1) + 0.5), 0), w - 1)
                    grid[r_idx, c_idx] = 1

    bits_str = "".join(map(str, grid.flatten().tolist()))
    return int(bits_str, 2)


def ink_hash_hex(strokes: Sequence[Any], w: int = 32, h: int = 8) -> str:
    """Retourne le ink_hash 256 bits sous forme hexadécimale fixe de 64 caractères."""
    val = ink_hash(strokes, w=w, h=h)
    return f"{val:064x}"


def _to_int_hash(val: int | str | None) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            return int(s, 16) if len(s) == 64 or any(c in "abcdefABCDEF" for c in s) else int(s)
        except ValueError:
            return None
    return None


def hamming(a: int | str, b: int | str) -> int:
    """Distance de Hamming entre deux ink_hash de 256 bits."""
    ia = _to_int_hash(a)
    ib = _to_int_hash(b)
    if ia is None or ib is None:
        return 256
    return (ia ^ ib).bit_count()


def _match_case_if_latin(target: str, source: str, lang: str) -> str:
    if (lang or "").lower().startswith("ar") or _AR_CHARS.search(target):
        return target
    if source.isupper() and len(source) > 1:
        return target.upper()
    if source.istitle():
        return target.capitalize()
    return target


class CorrectionLayer:
    """
    Couche de correction appliquée systématiquement APRÈS le cache et le post-traitement.
    1) Mémoire de ligne (L0 : exact + ink_hash proche) -> source = "memory"
    2) Dictionnaire personnel (L1 : par mot dès la 1re correction) -> source = "dictionary"
    """

    def __init__(self, line_mem=None, user_dict_module=None):
        self._line_mem = line_mem
        self._user_dict = user_dict_module

    @property
    def line_memory(self):
        if self._line_mem is None:
            from app.domain.line_memory import line_memory
            return line_memory
        return self._line_mem

    @property
    def user_dict(self):
        if self._user_dict is None:
            from app.domain import user_dictionary
            return user_dictionary
        return self._user_dict

    def apply(
        self,
        user_id: Optional[str],
        lang: str,
        strokes: Sequence[Any],
        result: Any,
        user_subs: Optional[dict] = None,
    ) -> Any:
        if not user_id or user_id in ("anon", "usr-guest"):
            return result

        lang = (lang or "fr").lower()
        from app.ml.cache import stroke_fingerprint
        fp = stroke_fingerprint(strokes) if strokes else ""
        ih_hex = ink_hash_hex(strokes) if strokes else ""

        # ── 1) L0 : Mémoire de ligne (exacte puis tolérante ink_hash) ─────────
        hit_text = self.line_memory.lookup(
            user_id=user_id,
            stroke_fingerprint=fp,
            ink_hash_val=ih_hex,
            lang=lang,
        )
        if hit_text:
            self._apply_memory_hit(result, hit_text)
            self._record_metric_applied(lang, "memory")
            return result

        # ── 2) L1 : Dictionnaire personnel (dès la 1re correction) ────────────
        if user_subs is None:
            user_subs = self.user_dict.load_user_subs_for_id(user_id, lang)

        if not user_subs:
            return result

        # Construire une table indexée par normalize_key
        norm_subs = {}
        for k, val in user_subs.items():
            right_txt = val[0] if isinstance(val, (tuple, list)) else str(val)
            norm_subs[normalize_key(k, lang)] = right_txt

        # 2a) Vérifier si la ligne entière correspond à une entrée du dictionnaire
        line_text = self._get_text(result)
        line_norm = normalize_key(line_text, lang)
        if line_norm and line_norm in norm_subs:
            fixed_line = norm_subs[line_norm]
            self._apply_dictionary_line_hit(result, fixed_line)
            self._record_metric_applied(lang, "dictionary")
            return result

        # 2b) Vérifier mot par mot dès la 1re correction
        words = self._get_words(result)
        any_word_fixed = False
        for w in words:
            w_txt = self._get_word_text(w)
            w_norm = normalize_key(w_txt, lang)
            if w_norm and w_norm in norm_subs:
                fix = norm_subs[w_norm]
                new_w_txt = _match_case_if_latin(fix, w_txt, lang)
                self._set_word_correction(w, new_w_txt, original=w_txt, source="dictionary")
                any_word_fixed = True

        if any_word_fixed:
            new_full = " ".join(self._get_word_text(w) for w in words)
            self._set_text(result, new_full)
            self._set_source(result, "dictionary")
            self._record_metric_applied(lang, "dictionary")

        return result

    @staticmethod
    def _record_metric_applied(lang: str, source: str) -> None:
        try:
            from app.core.metrics import metrics_collector
            metrics_collector.record_correction_applied(lang=lang, source=source)
        except Exception:
            pass

    @staticmethod
    def _get_text(result: Any) -> str:
        if isinstance(result, dict):
            return result.get("text", "")
        return getattr(result, "text", "") or ""

    @staticmethod
    def _set_text(result: Any, text: str) -> None:
        if isinstance(result, dict):
            result["text"] = text
        else:
            result.text = text

    @staticmethod
    def _set_source(result: Any, source: str) -> None:
        if isinstance(result, dict):
            result["source"] = source
            result["calibrated"] = False
        else:
            if hasattr(result, "source"):
                result.source = source
            if hasattr(result, "calibrated"):
                result.calibrated = False

    @staticmethod
    def _get_words(result: Any) -> list:
        if isinstance(result, dict):
            return result.get("words", [])
        return getattr(result, "words", []) or []

    @staticmethod
    def _get_word_text(w: Any) -> str:
        if isinstance(w, dict):
            return w.get("text", "")
        return getattr(w, "text", "") or ""

    @staticmethod
    def _set_word_correction(w: Any, new_text: str, original: str, source: str) -> None:
        if isinstance(w, dict):
            if not w.get("original"):
                w["original"] = original
            w["text"] = new_text
            w["corrected"] = True
            w["source"] = source
        else:
            if not getattr(w, "original", None):
                w.original = original
            w.text = new_text
            w.corrected = True
            if hasattr(w, "source"):
                w.source = source

    def _apply_memory_hit(self, result: Any, hit_text: str) -> None:
        self._set_text(result, hit_text)
        self._set_source(result, "memory")
        if isinstance(result, dict):
            result["confidence"] = 1.0
            result["min_word_confidence"] = 1.0
            result["words"] = [
                {
                    "index": i,
                    "text": tok,
                    "confidence": 1.0,
                    "calibrated": False,
                    "alternatives": [],
                    "bbox": None,
                    "corrected": True,
                    "original": None,
                    "source": "memory",
                }
                for i, tok in enumerate(hit_text.split())
            ]
        else:
            result.confidence = 1.0
            if hasattr(result, "min_word_confidence"):
                result.min_word_confidence = 1.0
            existing_words = getattr(result, "words", [])
            from app.schemas.recognition import WordResult
            from app.ml.engines.base import WordOut
            use_word_out = bool(existing_words and isinstance(existing_words[0], WordOut))
            new_words = []
            for i, tok in enumerate(hit_text.split()):
                if use_word_out:
                    new_words.append(
                        WordOut(
                            index=i,
                            text=tok,
                            confidence=1.0,
                            alternatives=[],
                            bbox=None,
                            corrected=True,
                            original=None,
                            source="memory",
                        )
                    )
                else:
                    new_words.append(
                        WordResult(
                            index=i,
                            text=tok,
                            confidence=1.0,
                            calibrated=False,
                            alternatives=[],
                            bbox=None,
                            corrected=True,
                            original=None,
                            source="memory",
                        )
                    )
            result.words = new_words

    def _apply_dictionary_line_hit(self, result: Any, fixed_text: str) -> None:
        orig_text = self._get_text(result)
        self._set_text(result, fixed_text)
        self._set_source(result, "dictionary")
        words = self._get_words(result)
        tokens = fixed_text.split()
        if len(words) == len(tokens):
            for w, tok in zip(words, tokens):
                self._set_word_correction(w, tok, original=self._get_word_text(w), source="dictionary")
        elif words:
            # Remplacer les mots par les tokens corrigés
            if isinstance(result, dict):
                result["words"] = [
                    {
                        "index": i,
                        "text": tok,
                        "confidence": 1.0,
                        "calibrated": False,
                        "alternatives": [],
                        "bbox": None,
                        "corrected": True,
                        "original": orig_text if i == 0 else None,
                        "source": "dictionary",
                    }
                    for i, tok in enumerate(tokens)
                ]
            else:
                from app.schemas.recognition import WordResult
                from app.ml.engines.base import WordOut
                use_word_out = isinstance(words[0], WordOut)
                new_words = []
                for i, tok in enumerate(tokens):
                    if use_word_out:
                        new_words.append(
                            WordOut(
                                index=i,
                                text=tok,
                                confidence=1.0,
                                alternatives=[],
                                bbox=None,
                                corrected=True,
                                original=orig_text if i == 0 else None,
                                source="dictionary",
                            )
                        )
                    else:
                        new_words.append(
                            WordResult(
                                index=i,
                                text=tok,
                                confidence=1.0,
                                calibrated=False,
                                alternatives=[],
                                bbox=None,
                                corrected=True,
                                original=orig_text if i == 0 else None,
                                source="dictionary",
                            )
                        )
                result.words = new_words


correction_layer = CorrectionLayer()
