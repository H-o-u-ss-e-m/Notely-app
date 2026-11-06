"""
HandwritingService v3 — Orchestrateur du pipeline HTR complet (ML-1, ML-2, ML-3, ML-4, ML-8, ML-10, ML-12a).
- Routage actif par langue via EngineRegistry
- Cache précis par empreinte de tracés et configuration (HtrCache)
- Rendu vectoriel configurable (RenderConfig)
- Détail par mot (WordResult), alternatives n-best et confiance calibrée
- Post-traitement Unicode, typographie et restauration d'accents
"""
import time
import logging
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image

from app.schemas.strokes import Stroke
from app.schemas.recognition import (
    RecognitionOptions,
    RecognitionResponse,
    LineRecognitionResult,
    WordResult,
    ReOCRLineRequest,
    LineWordsRequest,
)
from app.services.segmentation_service import segmentation_service
from app.ml.rendering import render_line, RenderConfig, compute_strokes_bbox
from app.ml.registry import registry
from app.ml.cache import line_cache_key, htr_cache, stroke_fingerprint
from app.domain.text_postprocess import postprocess_line
from app.domain.line_memory import line_memory
from app.domain.user_dictionary import get_user_dictionary_map
from app.services.vlm_fallback_service import vlm_fallback_service
from app.utils.image_utils import pil_to_webp_thumbnail
from app.core.config import settings

logger = logging.getLogger("handwriting_service_v3")


class HandwritingService:

    @staticmethod
    def process_strokes(
        strokes: List[Stroke],
        canvas_w: float,
        canvas_h: float,
        options: Optional[RecognitionOptions] = None,
        user_id: str = "anon",
    ) -> RecognitionResponse:
        """
        Pipeline OCR complet v3 :
        Strokes → Segmentation → Cache lookup → Rendu configurable → Registre de moteurs
        → Décodage avec mots & alternatives → Post-traitement par langue → Réponse enrichie.
        """
        start_time = time.time()

        if options is None:
            options = RecognitionOptions()

        lang = getattr(options, "language", "fr") or "fr"
        num_beams = getattr(options, "num_beams", 1) or 1
        include_b64 = getattr(options, "debug", False)
        include_thumbs = getattr(options, "include_thumbnails", False) or include_b64
        with_words = getattr(options, "with_words", True)

        if not strokes:
            return RecognitionResponse(
                success=True,
                processingTimeMs=0.0,
                lineCount=0,
                lines=[],
                fullText="",
                modelName=settings.TROCR_MODEL,
                modelVersion="v3",
                model_version="v3",
                language=lang,
            )

        # ── 1. Segmentation adaptative ─────────────────────────────────────────
        line_groups = segmentation_service.segment_strokes(strokes)
        if not line_groups:
            return RecognitionResponse(
                success=True,
                processingTimeMs=round((time.time() - start_time) * 1000, 2),
                lineCount=0,
                lines=[],
                fullText="",
                modelName=settings.TROCR_MODEL,
                modelVersion="v3",
                model_version="v3",
                language=lang,
            )

        # ── 2. Calcul de h_med pour normaliser l'épaisseur de trait ────────────
        all_heights = []
        for g in line_groups:
            for s in g["strokes"]:
                b = s.calculate_bbox()
                h = b.yMax - b.yMin
                if h > 2:
                    all_heights.append(h)
        h_med = float(np.median(all_heights)) if all_heights else None

        # ── 3. Configuration de rendu et routage par langue ────────────────────
        render_cfg = RenderConfig(
            padding_factor=getattr(settings, "PADDING_FACTOR", 0.25),
            render_scale=2,
            stroke_rel_width=0.06,
            deskew=getattr(options, "deskew", True),
            deskew_threshold_deg=getattr(settings, "DESKEW_THRESHOLD_DEG", 2.0),
            max_deskew_deg=getattr(settings, "MAX_DESKEW_DEG", 15.0),
            deslant=False,
            min_aspect_pad=True,
        )
        cfg_hash = render_cfg.hash()

        engine_chain, min_conf = registry.chain_for(lang)
        primary_engine_name = engine_chain[0] if engine_chain else "trocr_fr"
        engine = registry.get(primary_engine_name)

        # Charger le dictionnaire personnel de l'utilisateur (ML-5) et consentements (ML-11)
        user_subs = None
        consent_cloud_ocr = False
        if user_id and user_id not in ("anon", "usr-guest"):
            try:
                import uuid
                u_uuid = uuid.UUID(user_id)
                from app.db.session import SessionLocal
                from app.db.models.user_settings import UserSettings
                with SessionLocal() as db_sess:
                    user_subs = get_user_dictionary_map(db_sess, u_uuid, language=lang)
                    st = db_sess.query(UserSettings).filter(UserSettings.user_id == u_uuid).first()
                    if st:
                        consent_cloud_ocr = bool(st.consent_cloud_ocr)
            except Exception:
                user_subs = None
                consent_cloud_ocr = False

        # ── 4. Rendu, mémoire de ligne et vérification du cache ─────────────────
        rendered_images: List[Image.Image] = []
        thumbnails: List[str] = []
        cache_keys: List[str] = []
        cached_results: List[Optional[Dict[str, Any]]] = []
        uncached_indices: List[int] = []

        for idx, group in enumerate(line_groups):
            pil_crop, b64_str = render_line(
                strokes=group["strokes"],
                cfg=render_cfg,
                bbox=group["bbox"],
                slanted_angle=group["slanted_angle"],
                h_med=h_med,
                include_base64=include_b64,
            )
            rendered_images.append(pil_crop)
            # Générer miniature WebP compacte (≤ 8 Ko) si thumbnails demandées
            webp_thumb = pil_to_webp_thumbnail(pil_crop) if include_thumbs else None
            thumbnails.append(webp_thumb or b64_str)

            # Vérifier la mémoire de ligne exacte (§8.5.c)
            fp = stroke_fingerprint(group["strokes"])
            mem_text = line_memory.lookup(user_id, fp)
            if mem_text is not None:
                mem_words = [
                    {
                        "index": i,
                        "text": w,
                        "confidence": 1.0,
                        "alternatives": [],
                        "bbox": None,
                        "corrected": True,
                        "original": None,
                    }
                    for i, w in enumerate(mem_text.split())
                ]
                cache_dict = {
                    "text": mem_text,
                    "confidence": 1.0,
                    "min_word_confidence": 1.0,
                    "words": mem_words,
                    "alternatives": [],
                    "engine": "line_memory",
                    "model_version": "user",
                }
                cache_keys.append("")
                cached_results.append(cache_dict)
                continue

            # Clé de cache HTR exacte (ML-12a)
            k = line_cache_key(
                user_id=user_id,
                strokes=group["strokes"],
                engine=primary_engine_name,
                model_version=getattr(engine, "version", "v3"),
                render_cfg_hash=cfg_hash,
                num_beams=num_beams,
                lang=lang,
            )
            cache_keys.append(k)

            val = htr_cache.get(k)
            if val is not None:
                cached_results.append(val)
            else:
                cached_results.append(None)
                uncached_indices.append(idx)

        # ── 5. Inférence batch sur les lignes non présentes en cache ───────────
        if uncached_indices:
            images_to_infer = [rendered_images[i] for i in uncached_indices]
            raw_lines_out = engine.recognize_lines(
                images_to_infer,
                num_beams=num_beams,
                n_best=3,
                with_words=with_words,
            )

            # Post-traitement (ML-10, ML-5) et mise en cache (ML-12a)
            for idx_in_uncached, global_idx in enumerate(uncached_indices):
                line_out = raw_lines_out[idx_in_uncached]
                line_out = postprocess_line(line_out, lang=lang, user_subs=user_subs)

                # Repli VLM cloud avec garde-fous (ML-11 / §8.11)
                if line_out.confidence < min_conf and consent_cloud_ocr:
                    line_out = vlm_fallback_service.process_fallback(
                        image=rendered_images[global_idx],
                        lang=lang,
                        principal_line=line_out,
                        user_id=user_id,
                        consent_cloud_ocr=consent_cloud_ocr,
                    )

                # Sérialisation pour le cache
                cache_dict = {
                    "text": line_out.text,
                    "confidence": line_out.confidence,
                    "min_word_confidence": line_out.min_word_confidence,
                    "words": [
                        {
                            "index": w.index,
                            "text": w.text,
                            "confidence": w.confidence,
                            "alternatives": w.alternatives,
                            "bbox": w.bbox,
                            "corrected": w.corrected,
                            "original": w.original,
                        }
                        for w in line_out.words
                    ],
                    "alternatives": line_out.alternatives,
                    "engine": line_out.engine,
                    "model_version": line_out.model_version,
                }
                htr_cache.set(cache_keys[global_idx], cache_dict)
                cached_results[global_idx] = cache_dict

        # ── 6. Construction de la réponse finale ──────────────────────────────
        recognized_lines: List[LineRecognitionResult] = []
        full_text_parts: List[str] = []

        for idx, group in enumerate(line_groups):
            res = cached_results[idx]
            if not res:
                res = {
                    "text": "",
                    "confidence": 0.0,
                    "min_word_confidence": 0.0,
                    "words": [],
                    "alternatives": [],
                    "engine": primary_engine_name,
                    "model_version": getattr(engine, "version", "v3"),
                }

            words_pydantic = [
                WordResult(
                    index=w["index"],
                    text=w["text"],
                    confidence=float(w["confidence"]),
                    alternatives=w.get("alternatives", []),
                    bbox=w.get("bbox"),
                    corrected=w.get("corrected", False),
                    original=w.get("original"),
                )
                for w in res.get("words", [])
            ]

            b64_val = thumbnails[idx] if include_thumbs else None

            rec_line = LineRecognitionResult(
                id=group["id"],
                stroke_ids=group["stroke_ids"],
                bbox=group["bbox"],
                text=res["text"],
                confidence=round(float(res["confidence"]), 4),
                calibrated=False,
                min_word_confidence=round(float(res.get("min_word_confidence", res["confidence"])), 4),
                words=words_pydantic,
                alternatives=res.get("alternatives", []),
                thumbnail=b64_val,
                image_base64=b64_val if include_b64 else None,
                engine=res.get("engine", primary_engine_name),
                model_version=res.get("model_version", "v3"),
            )

            recognized_lines.append(rec_line)
            if res["text"]:
                full_text_parts.append(res["text"])

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return RecognitionResponse(
            success=True,
            processingTimeMs=elapsed_ms,
            lineCount=len(recognized_lines),
            lines=recognized_lines,
            fullText="\n".join(full_text_parts),
            modelName=primary_engine_name,
            modelVersion=getattr(engine, "version", "v3"),
            model_version=getattr(engine, "version", "v3"),
            language=lang,
            calibrated=False,
        )

    @staticmethod
    def process_line_words(request: LineWordsRequest, user_id: str = "anon") -> LineRecognitionResult:
        """
        Endpoint POST /api/v1/ocr/line-words (ML-3).
        Re-reconnaît une unique ligne avec détail exhaustif des mots et alternatives.
        """
        target_strokes = [s for s in request.strokes if s.id in request.stroke_ids]
        if not target_strokes:
            target_strokes = request.strokes
        if not target_strokes:
            raise ValueError("Aucun stroke fourni.")

        bbox = compute_strokes_bbox(target_strokes)
        lang = request.language or "fr"
        num_beams = max(1, min(4, request.num_beams))

        render_cfg = RenderConfig(
            padding_factor=0.25,
            render_scale=2,
            stroke_rel_width=0.06,
            deskew=True,
            min_aspect_pad=True,
        )

        pil_crop, b64_str = render_line(
            strokes=target_strokes,
            cfg=render_cfg,
            bbox=bbox,
            slanted_angle=0.0,
            include_base64=request.include_thumbnail,
        )

        engine_chain, _ = registry.chain_for(lang)
        primary_engine_name = engine_chain[0] if engine_chain else "trocr_fr"
        engine = registry.get(primary_engine_name)

        # Charger dictionnaire personnel utilisateur si connecté et consentements
        user_subs = None
        consent_cloud_ocr = False
        if user_id and user_id not in ("anon", "usr-guest"):
            try:
                import uuid
                u_uuid = uuid.UUID(user_id)
                from app.db.session import SessionLocal
                from app.db.models.user_settings import UserSettings
                with SessionLocal() as db_sess:
                    user_subs = get_user_dictionary_map(db_sess, u_uuid, language=lang)
                    st = db_sess.query(UserSettings).filter(UserSettings.user_id == u_uuid).first()
                    if st:
                        consent_cloud_ocr = bool(st.consent_cloud_ocr)
            except Exception:
                user_subs = None
                consent_cloud_ocr = False

        raw_lines = engine.recognize_lines(
            [pil_crop],
            num_beams=num_beams,
            n_best=3,
            with_words=True,
        )
        line_out = raw_lines[0] if raw_lines else None
        if line_out:
            line_out = postprocess_line(line_out, lang=lang, user_subs=user_subs)
            if line_out.confidence < 0.65 and consent_cloud_ocr:
                line_out = vlm_fallback_service.process_fallback(
                    image=pil_crop,
                    lang=lang,
                    principal_line=line_out,
                    user_id=user_id,
                    consent_cloud_ocr=consent_cloud_ocr,
                )

        words_pydantic = [
            WordResult(
                index=w.index,
                text=w.text,
                confidence=w.confidence,
                alternatives=w.alternatives,
                bbox=w.bbox,
                corrected=w.corrected,
                original=w.original,
            )
            for w in (line_out.words if line_out else [])
        ]

        webp_thumb = pil_to_webp_thumbnail(pil_crop) if request.include_thumbnail else None

        return LineRecognitionResult(
            id=1,
            stroke_ids=request.stroke_ids,
            bbox=bbox,
            text=line_out.text if line_out else "",
            confidence=round(line_out.confidence, 4) if line_out else 0.0,
            calibrated=False,
            min_word_confidence=round(line_out.min_word_confidence, 4) if line_out else 0.0,
            words=words_pydantic,
            alternatives=line_out.alternatives if line_out else [],
            thumbnail=webp_thumb,
            image_base64=b64_str,
            engine=primary_engine_name,
            model_version=getattr(engine, "version", "v3"),
        )

    @staticmethod
    def reocr_line(request: ReOCRLineRequest) -> LineRecognitionResult:
        """Rétrocompatibilité pour /reocr-line."""
        lw_req = LineWordsRequest(
            stroke_ids=request.stroke_ids,
            strokes=request.strokes,
            language="fr",
            num_beams=1,
            include_thumbnail=True,
            canvasWidth=request.canvasWidth,
            canvasHeight=request.canvasHeight,
        )
        return HandwritingService.process_line_words(lw_req)


handwriting_service = HandwritingService()
