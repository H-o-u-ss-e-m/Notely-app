"""
TrOCR Engine v2 — Moteur de reconnaissance d'écriture manuscrite.

Améliorations par rapport à v1 :
  - torch.inference_mode() au lieu de torch.no_grad() (plus efficace)
  - max_new_tokens=128 (évite la troncature des lignes françaises accentuées)
  - recognize_lines() : traitement par lots (batch) — toutes les lignes en un seul passage
  - Beam search configurable via num_beams (1=greedy rapide, 4=plus précis)
  - Cache LRU (512 entrées) par empreinte d'image pour éviter de recalculer des lignes inchangées
  - FP16 automatique si GPU CUDA disponible
  - Confiance par mot via compute_transition_scores (méthode dédiée)
  - Beam search : utilise sequences_scores (log-prob totale) pour une confiance plus fiable
"""
import torch
import hashlib
import logging
from collections import OrderedDict
from PIL import Image
from typing import List, Tuple, Dict, Optional
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from app.core.config import settings
from app.core.device import get_optimal_device

logger = logging.getLogger("trocr_engine")

# ── Cache LRU borné ────────────────────────────────────────────────────────────
_LINE_CACHE_MAX = 512  # entrées max
_line_cache: "OrderedDict[str, Tuple[str, float]]" = OrderedDict()


def _image_fingerprint(pil_img: Image.Image) -> str:
    """Empreinte SHA-1 légère : resize 64×16 avant hash (rapide, suffisamment discriminant)."""
    thumb = pil_img.convert("L").resize((64, 16))
    return hashlib.sha1(thumb.tobytes()).hexdigest()


def _cache_get(key: str) -> Optional[Tuple[str, float]]:
    if key in _line_cache:
        _line_cache.move_to_end(key)
        return _line_cache[key]
    return None


def _cache_set(key: str, value: Tuple[str, float]) -> None:
    if key in _line_cache:
        _line_cache.move_to_end(key)
    _line_cache[key] = value
    if len(_line_cache) > _LINE_CACHE_MAX:
        _line_cache.popitem(last=False)  # evict le plus ancien


class TrOCREngine:
    """
    Gestionnaire d'inférence TrOCR singleton (v2).
    Chargé UNE SEULE FOIS au démarrage du backend.
    """

    def __init__(self):
        self.processor: Optional[TrOCRProcessor] = None
        self.model: Optional[VisionEncoderDecoderModel] = None
        self.device: str = get_optimal_device()
        self.model_name: str = settings.TROCR_MODEL
        self.use_fp16: bool = (self.device == "cuda")
        self.model_version: str = "v2"

    # ── Chargement ────────────────────────────────────────────────────────────

    def load_model(self) -> None:
        """Charge les poids pré-entraînés depuis HuggingFace (ou cache local)."""
        if self.model is not None and self.processor is not None:
            logger.info("Modèle TrOCR déjà en mémoire — chargement ignoré.")
            return

        logger.info(
            f"Chargement TrOCR [{self.model_name}] sur {self.device.upper()} "
            f"(FP16={'oui' if self.use_fp16 else 'non'}) ..."
        )
        torch_dtype = torch.float16 if self.use_fp16 else torch.float32
        try:
            try:
                # Essayer d'abord le cache local sans connexion réseau
                self.processor = TrOCRProcessor.from_pretrained(self.model_name, local_files_only=True)
                self.model = VisionEncoderDecoderModel.from_pretrained(
                    self.model_name, torch_dtype=torch_dtype, local_files_only=True
                )
            except Exception:
                self.processor = TrOCRProcessor.from_pretrained(self.model_name)
                self.model = VisionEncoderDecoderModel.from_pretrained(
                    self.model_name, torch_dtype=torch_dtype
                )
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"✅ TrOCR [{self.model_name}] prêt sur {self.device.upper()}.")
        except Exception as e:
            logger.error(f"❌ Erreur chargement TrOCR : {e}")
            raise

    # ── Inférence d'une seule ligne (rétrocompatibilité) ─────────────────────

    def recognize_line(
        self,
        pil_image: Image.Image,
        num_beams: int = 1,
        use_cache: bool = True,
    ) -> Tuple[str, float]:
        """
        Reconnaît le texte d'une image PIL d'une seule ligne.
        Appelle recognize_lines() en interne.

        Args:
            pil_image : image PIL RGB (fond blanc, texte noir)
            num_beams : 1=greedy (rapide), >1=beam search (plus précis)
            use_cache : utilise le cache LRU si True

        Returns:
            (texte, confiance) — confiance ∈ [0, 1]
        """
        results = self.recognize_lines(
            [pil_image], num_beams=num_beams, use_cache=use_cache
        )
        return results[0] if results else ("", 0.0)

    # ── Inférence par lots ────────────────────────────────────────────────────

    def recognize_lines(
        self,
        images: List[Image.Image],
        num_beams: int = 1,
        batch_size: int = 8,
        max_new_tokens: int = 128,
        use_cache: bool = True,
    ) -> List[Tuple[str, float]]:
        """
        Reconnaît plusieurs lignes en un ou plusieurs passages GPU/CPU.

        Args:
            images        : liste d'images PIL RGB
            num_beams     : 1=greedy, 4=beam (mieux sur GPU ; limité à 2 sur CPU)
            batch_size    : taille des micro-lots (réduire si OOM)
            max_new_tokens: limite de tokens par ligne (128 pour éviter troncature FR)
            use_cache     : cache LRU par empreinte d'image

        Returns:
            liste de (texte, confiance) dans le même ordre que images
        """
        if self.model is None or self.processor is None:
            self.load_model()

        # Limiter le beam search sur CPU pour éviter une latence excessive
        if self.device == "cpu" and num_beams > 2:
            logger.debug(f"CPU détecté : num_beams réduit de {num_beams} à 2.")
            num_beams = 2

        results: List[Optional[Tuple[str, float]]] = [None] * len(images)
        pending_indices: List[int] = []
        fingerprints: List[str] = []

        # ── 1. Vérifier le cache pour chaque image ────────────────────────────
        for idx, img in enumerate(images):
            rgb = img.convert("RGB")
            fp = (
                _image_fingerprint(rgb)
                + f"|{self.model_name}|{num_beams}|{max_new_tokens}"
            )
            fingerprints.append(fp)
            if use_cache:
                cached = _cache_get(fp)
                if cached is not None:
                    results[idx] = cached
                    continue
            pending_indices.append(idx)

        if not pending_indices:
            logger.debug("Toutes les lignes servies depuis le cache LRU.")
            return results  # type: ignore

        # ── 2. Inférence par micro-lots pour les lignes non cachées ──────────
        for batch_start in range(0, len(pending_indices), batch_size):
            batch_idx = pending_indices[batch_start: batch_start + batch_size]
            batch_imgs = [images[i].convert("RGB") for i in batch_idx]

            try:
                pv = self.processor(
                    images=batch_imgs, return_tensors="pt"
                ).pixel_values

                if self.use_fp16:
                    pv = pv.half()
                pv = pv.to(self.device)

                with torch.inference_mode():
                    out = self.model.generate(
                        pv,
                        num_beams=num_beams,
                        max_new_tokens=max_new_tokens,
                        early_stopping=(num_beams > 1),
                        return_dict_in_generate=True,
                        output_scores=True,
                    )

                texts = self.processor.batch_decode(
                    out.sequences, skip_special_tokens=True
                )

                # ── Calcul de la confiance ────────────────────────────────────
                # Beam search  : sequences_scores = log-prob totale → exp = prob géométrique
                # Greedy       : moyenne des max(softmax) sur les tokens générés
                if num_beams > 1 and hasattr(out, "sequences_scores") and out.sequences_scores is not None:
                    confs = torch.exp(out.sequences_scores).tolist()
                else:
                    if out.scores:
                        stacked = torch.stack(out.scores, dim=1).float()  # [B, T, V]
                        probs = torch.softmax(stacked, dim=-1)
                        max_probs = torch.max(probs, dim=-1).values       # [B, T]
                        confs = torch.mean(max_probs, dim=-1).tolist()
                    else:
                        confs = [0.95] * len(batch_imgs)

                for global_i, text, conf in zip(batch_idx, texts, confs):
                    entry = (text.strip(), round(float(conf), 4))
                    results[global_i] = entry
                    if use_cache:
                        _cache_set(fingerprints[global_i], entry)

            except Exception as e:
                logger.error(f"Erreur inférence TrOCR (batch) : {e}")
                for global_i in batch_idx:
                    if results[global_i] is None:
                        results[global_i] = ("", 0.0)

        # Sécurité : remplacer les None restants
        return [r if r is not None else ("", 0.0) for r in results]

    # ── Confiance par mot ─────────────────────────────────────────────────────

    def recognize_line_with_word_scores(
        self, pil_image: Image.Image, max_new_tokens: int = 128
    ) -> Tuple[str, float, List[Dict]]:
        """
        Reconnaît une ligne et retourne en plus les scores par mot.
        Utilise le décodage greedy (requis pour compute_transition_scores).

        Returns:
            (texte_complet, confiance_globale, liste_mots)
            liste_mots = [{"word": str, "confidence": float}, ...]
        """
        if self.model is None or self.processor is None:
            self.load_model()

        img = pil_image.convert("RGB")
        pv = self.processor(images=img, return_tensors="pt").pixel_values
        if self.use_fp16:
            pv = pv.half()
        pv = pv.to(self.device)

        try:
            with torch.inference_mode():
                out = self.model.generate(
                    pv,
                    num_beams=1,              # greedy requis pour compute_transition_scores
                    max_new_tokens=max_new_tokens,
                    return_dict_in_generate=True,
                    output_scores=True,
                )

            text = self.processor.batch_decode(
                out.sequences, skip_special_tokens=True
            )[0].strip()

            # Probabilité de chaque token généré
            token_scores = self.model.compute_transition_scores(
                out.sequences, out.scores, normalize_logits=True
            )
            tok_probs = torch.exp(token_scores[0]).tolist()
            token_ids = out.sequences[0][1:].tolist()  # retire BOS
            tokens = self.processor.tokenizer.convert_ids_to_tokens(token_ids)

            # Regrouper par mot (token commençant par 'Ġ' = nouveau mot en BPE RoBERTa)
            words: List[Dict] = []
            cur_tok: List[str] = []
            cur_prob: List[float] = []

            for tok, prob in zip(tokens, tok_probs):
                if tok in ("</s>", "<pad>", "<eos>"):
                    break
                if tok.startswith("Ġ") and cur_tok:
                    word_text = "".join(cur_tok).replace("Ġ", "")
                    words.append({"word": word_text, "confidence": round(min(cur_prob), 4)})
                    cur_tok, cur_prob = [], []
                cur_tok.append(tok)
                cur_prob.append(prob)

            if cur_tok:
                word_text = "".join(cur_tok).replace("Ġ", "")
                words.append({"word": word_text, "confidence": round(min(cur_prob), 4)})

            global_conf = (
                round(float(sum(p["confidence"] for p in words) / len(words)), 4)
                if words else 0.0
            )
            return text, global_conf, words

        except Exception as e:
            logger.error(f"Erreur recognize_line_with_word_scores : {e}")
            return "", 0.0, []

    # ── Gestion du cache ──────────────────────────────────────────────────────

    def clear_cache(self) -> int:
        """Vide le cache LRU. Retourne le nombre d'entrées supprimées."""
        count = len(_line_cache)
        _line_cache.clear()
        logger.info(f"Cache TrOCR vidé ({count} entrées).")
        return count

    @property
    def cache_size(self) -> int:
        return len(_line_cache)


# Singleton — instancié une seule fois au démarrage du backend
trocr_engine = TrOCREngine()
