"""
Moteur TrOCR conforme au protocole OcrEngine (ML-1, ML-3, ML-4).
Gère la reconnaissance par lots, l'extraction des mots par BPE RoBERTa,
la confiance calibrée et les alternatives n-best.
"""
import gc
import math
import logging
import torch
from typing import List, Sequence, Optional, Tuple
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from app.ml.engines.base import OcrEngine, LineOut, WordOut
from app.core.device import get_optimal_device
from app.core.config import settings

logger = logging.getLogger("trocr_engine_v3")


def group_tokens_to_words(tokens: List[str], probs: List[float]) -> List[Tuple[str, float]]:
    """
    BPE RoBERTa : un token commençant par 'Ġ' ouvre un nouveau mot.
    Confiance du mot = probabilité MINIMALE de ses tokens.
    """
    words: List[Tuple[str, float]] = []
    cur_t: List[str] = []
    cur_p: List[float] = []

    for t, p in zip(tokens, probs):
        if t in ("</s>", "<pad>", "<s>", "<eos>"):
            if t in ("</s>", "<eos>"):
                break
            continue
        if t.startswith("Ġ") and cur_t:
            w_text = "".join(cur_t).replace("Ġ", "")
            if w_text:
                words.append((w_text, max(0.0, min(1.0, float(min(cur_p))))))
            cur_t, cur_p = [], []
        cur_t.append(t)
        cur_p.append(p)

    if cur_t:
        w_text = "".join(cur_t).replace("Ġ", "")
        if w_text:
            words.append((w_text, max(0.0, min(1.0, float(min(cur_p))))))

    return words


class TrOCROcrEngine:
    """Moteur OCR basé sur HuggingFace VisionEncoderDecoderModel (TrOCR)."""

    def __init__(
        self,
        name: str = "trocr_fr",
        model_name: str = "microsoft/trocr-base-handwritten",
        languages: Tuple[str, ...] = ("fr", "en"),
        version: str = "v3",
    ):
        self.name = name
        self.model_name = model_name
        self.version = version
        self.languages = frozenset(languages)
        self.device = get_optimal_device()
        self.use_fp16 = (self.device == "cuda")
        self.processor: Optional[TrOCRProcessor] = None
        self.model: Optional[VisionEncoderDecoderModel] = None

    def _ensure_loaded(self) -> None:
        if self.model is not None and self.processor is not None:
            return
        logger.info(f"Chargement du moteur {self.name} [{self.model_name}]...")
        torch_dtype = torch.float16 if self.use_fp16 else torch.float32
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

        # ML-12b : Quantification int8 dynamique sur CPU (§8.12.b)
        if self.device == "cpu" and getattr(settings, "QUANTIZE_INT8_CPU", True):
            try:
                import torch.ao.quantization as tq
                logger.info(f"Quantification int8 dynamique de {self.name} sur CPU...")
                self.model = tq.quantize_dynamic(
                    self.model, {torch.nn.Linear}, dtype=torch.qint8
                )
            except Exception as e:
                logger.warning(f"Quantification int8 non appliquée : {e}")

        # Warm-up immédiat du modèle (supprime la latence de la première requête)
        try:
            dummy = Image.new("RGB", (384, 64), color=(255, 255, 255))
            pv_dummy = self.processor(images=[dummy], return_tensors="pt").pixel_values
            if self.use_fp16:
                pv_dummy = pv_dummy.half()
            pv_dummy = pv_dummy.to(self.device)
            _ = self.model.generate(pv_dummy, max_new_tokens=4, num_beams=1)
            logger.info(f"Warm-up de {self.name} terminé avec succès.")
        except Exception as e:
            logger.debug(f"Warm-up optionnel ignoré : {e}")

    def unload(self) -> None:
        """Libère la mémoire GPU/CPU."""
        logger.info(f"Déchargement du moteur {self.name}...")
        self.model = None
        self.processor = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    @torch.inference_mode()
    def recognize_lines(
        self,
        images: Sequence[Image.Image],
        *,
        num_beams: int = 1,
        n_best: int = 3,
        with_words: bool = True,
    ) -> List[LineOut]:
        if not images:
            return []

        self._ensure_loaded()
        assert self.model is not None and self.processor is not None

        # Limiter num_beams sur CPU pour éviter une latence prohibitive
        if self.device == "cpu" and num_beams > 2:
            num_beams = 2

        # ML-12b : Tri des images par largeur pour réduire le padding du batch
        indexed_images = list(enumerate(images))
        indexed_images.sort(key=lambda t: t[1].size[0])
        sorted_images = [t[1] for t in indexed_images]

        results_sorted: List[LineOut] = []
        batch_size = 2 if self.device == "cpu" else 4

        for start_idx in range(0, len(sorted_images), batch_size):
            batch_imgs = [img.convert("RGB") for img in sorted_images[start_idx: start_idx + batch_size]]
            pv = self.processor(images=batch_imgs, return_tensors="pt").pixel_values
            if self.use_fp16:
                pv = pv.half()
            pv = pv.to(self.device)

            actual_n_best = min(n_best, num_beams) if num_beams > 1 else 1

            try:
                gen = self.model.generate(
                    pv,
                    num_beams=num_beams,
                    num_return_sequences=actual_n_best,
                    max_new_tokens=128,
                    early_stopping=(num_beams > 1),
                    return_dict_in_generate=True,
                    output_scores=True,
                )

                # Calcul des transition scores si disponible
                trans_scores = None
                try:
                    if num_beams == 1:
                        trans_scores = self.model.compute_transition_scores(
                            gen.sequences, gen.scores, normalize_logits=True
                        )
                    elif hasattr(gen, "beam_indices") and gen.beam_indices is not None:
                        trans_scores = self.model.compute_transition_scores(
                            gen.sequences, gen.scores, gen.beam_indices, normalize_logits=False
                        )
                except Exception as ex:
                    logger.debug(f"Transition scores non calculables: {ex}")

                # Décoder les séquences
                seqs = gen.sequences
                batch_count = len(batch_imgs)
                seqs_reshaped = seqs.view(batch_count, actual_n_best, -1)

                for b in range(batch_count):
                    best_seq = seqs_reshaped[b, 0]
                    decoded_best = self.processor.decode(best_seq, skip_special_tokens=True).strip()

                    # Alternatives n-best
                    alts: List[str] = []
                    for k in range(actual_n_best):
                        alt_text = self.processor.decode(seqs_reshaped[b, k], skip_special_tokens=True).strip()
                        if alt_text and alt_text not in alts and alt_text != decoded_best:
                            alts.append(alt_text)

                    # Extraction des mots et probabilités
                    words_out: List[WordOut] = []
                    min_word_c = 0.95
                    weighted_c = 0.95

                    if with_words and trans_scores is not None:
                        # Extraire les tokens et probas
                        token_ids = best_seq[1:].tolist()  # skip BOS
                        tokens = self.processor.tokenizer.convert_ids_to_tokens(token_ids)
                        b_trans = trans_scores[b * actual_n_best] if len(trans_scores) > b * actual_n_best else None
                        
                        if b_trans is not None:
                            probs = torch.exp(b_trans).tolist()
                            grouped = group_tokens_to_words(tokens, probs)
                            
                            for w_idx, (w_str, w_conf) in enumerate(grouped):
                                words_out.append(WordOut(
                                    index=w_idx,
                                    text=w_str,
                                    confidence=round(w_conf, 4),
                                    alternatives=[],
                                    bbox=None,
                                    corrected=False,
                                ))

                            if words_out:
                                min_word_c = min(w.confidence for w in words_out)
                                total_chars = sum(len(w.text) for w in words_out)
                                if total_chars > 0:
                                    weighted_c = sum(w.confidence * len(w.text) for w in words_out) / total_chars
                                else:
                                    weighted_c = sum(w.confidence for w in words_out) / len(words_out)

                    # Si pas de mots extraits via transition_scores, découpage sur espaces
                    if not words_out:
                        raw_words = decoded_best.split()
                        fallback_c = 0.90
                        if num_beams > 1 and hasattr(gen, "sequences_scores") and gen.sequences_scores is not None:
                            try:
                                fallback_c = float(torch.exp(gen.sequences_scores[b * actual_n_best]).item())
                                fallback_c = max(0.1, min(1.0, fallback_c))
                            except Exception:
                                pass
                        
                        for w_idx, w_str in enumerate(raw_words):
                            words_out.append(WordOut(
                                index=w_idx,
                                text=w_str,
                                confidence=round(fallback_c, 4),
                                alternatives=[],
                                bbox=None,
                                corrected=False,
                            ))
                        min_word_c = fallback_c
                        weighted_c = fallback_c

                    # Formule ML-4 (§8.4) : 0.5 * weighted_mean + 0.5 * min_word_confidence
                    line_conf = round(0.5 * weighted_c + 0.5 * min_word_c, 4)

                    results_sorted.append(LineOut(
                        text=decoded_best,
                        confidence=line_conf,
                        min_word_confidence=round(min_word_c, 4),
                        words=words_out,
                        alternatives=alts[:3],
                        engine=self.name,
                        model_version=self.version,
                    ))

            except Exception as e:
                logger.error(f"Erreur batch TrOCR: {e}")
                for _ in range(len(batch_imgs)):
                    results_sorted.append(LineOut(
                        text="",
                        confidence=0.0,
                        min_word_confidence=0.0,
                        words=[],
                        alternatives=[],
                        engine=self.name,
                        model_version=self.version,
                    ))

        # Réordonnancement dans l'ordre d'origine
        reordered: List[Optional[LineOut]] = [None] * len(images)
        for sorted_idx, (orig_idx, _) in enumerate(indexed_images):
            if sorted_idx < len(results_sorted):
                reordered[orig_idx] = results_sorted[sorted_idx]
        return [r for r in reordered if r is not None]
