# -*- coding: utf-8 -*-
import re
import time
import numpy as np
from typing import List
from app.schemas.strokes import Stroke
from app.schemas.structural import StructuralElement, StructuralHTRRequest, StructuralHTRResponse, PageData
from app.services.segmentation_service import segmentation_service
from app.services.image_service import image_service
from app.services.ocr_service import ocr_service
from app.ml.registry import registry
from app.ml.cache import stroke_fingerprint
from app.domain.text_postprocess import postprocess_line
from app.domain.correction_layer import correction_layer
from app.domain.user_dictionary import get_user_dictionary_map
from app.utils.image_utils import pil_to_webp_thumbnail
from app.schemas.recognition import WordResult

class StructuralHTRService:
    ROMAN_REGEX = re.compile(r'^(I|II|III|IV|V|VI|VII|VIII|IX|X)\s*[\.\-\:\)]\s*', re.IGNORECASE)
    SUBTITLE_REGEX = re.compile(r'^(\d+[\.\-\)]|[A-Z][\.\-\)]|\d+\.\d+)\s*', re.IGNORECASE)

    @staticmethod
    def _clean_base64_string(b64_str: str) -> str:
        if not b64_str:
            return ""
        if "," in b64_str:
            return b64_str.split(",", 1)[1].strip()
        return b64_str.strip()

    def process_structural_strokes(self, request: StructuralHTRRequest, user_id: str = "anon") -> StructuralHTRResponse:
        start_time = time.time()
        lang = getattr(request, "language", "fr") or "fr"

        user_subs = None
        if user_id and user_id not in ("anon", "usr-guest"):
            try:
                import uuid
                u_uuid = uuid.UUID(str(user_id))
                from app.db.session import SessionLocal
                with SessionLocal() as db_sess:
                    user_subs = get_user_dictionary_map(db_sess, u_uuid, language=lang)
            except Exception:
                user_subs = None
        
        # Obtenir la liste des pages
        pages: List[PageData] = []
        if request.pages and len(request.pages) > 0:
            pages = request.pages
        elif request.strokes:
            pages = [PageData(
                pageNumber=1,
                strokes=request.strokes,
                width=request.canvasWidth,
                height=request.canvasHeight
            )]

        if not pages:
            return StructuralHTRResponse(
                success=True,
                processingTimeMs=0.0,
                subject=request.subject or "Cours Manuscrit",
                lessonTitle=request.lessonTitle or "Nouveau Cours",
                elements=[],
                fullMarkdown=""
            )

        all_elements: List[StructuralElement] = []
        markdown_lines: List[str] = []
        elem_counter = 1

        for page in pages:
            strokes = page.strokes
            if not strokes:
                continue

            canvas_w = page.width or request.canvasWidth
            canvas_h = page.height or request.canvasHeight

            # Groupement adaptatif des strokes par ligne
            line_groups = segmentation_service.segment_strokes(strokes)
            if not line_groups:
                continue

            line_groups = sorted(line_groups, key=lambda g: g["bbox"][1])
            heights = [g["bbox"][3] - g["bbox"][1] for g in line_groups]
            median_height = float(np.median(heights)) if heights else 30.0

            for idx, group in enumerate(line_groups, start=1):
                bbox = group["bbox"]
                group_strokes = group["strokes"]
                stroke_ids = group["stroke_ids"]
                height = bbox[3] - bbox[1]
                width = bbox[2] - bbox[0]
                center_x = (bbox[0] + bbox[2]) / 2.0
                top_y = bbox[1]

                # Détection d'un contentType explicite H1..H6 ou Schéma sur les strokes
                explicit_type = None
                for s in group_strokes:
                    c_type = (getattr(s, 'contentType', '') or '').lower()
                    tool = (getattr(s, 'tool', '') or '').lower()
                    if c_type in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        explicit_type = c_type
                        break
                    elif tool in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        explicit_type = tool
                        break

                has_diagram_tool = any(getattr(s, 'tool', 'pen') == 'diagram' for s in group_strokes)

                # Rendu du crop de haute qualité
                pil_crop, raw_b64_url = image_service.render_line_crop(
                    strokes=group_strokes,
                    bbox=bbox,
                    slanted_angle=group.get("slanted_angle", 0.0),
                    canvas_width=canvas_w,
                    canvas_height=canvas_h
                )
                clean_b64 = self._clean_base64_string(raw_b64_url)

                # 1. Traitement des Schémas / Dessins Géométriques
                if has_diagram_tool or (height > 2.0 * median_height and width > 80.0 and len(group_strokes) >= 4):
                    elem = StructuralElement(
                        id=elem_counter,
                        type="diagram",
                        text="[Schéma / Dessin Géométrique]",
                        confidence=1.0,
                        bbox=bbox,
                        image_base64=clean_b64,
                        stroke_ids=stroke_ids,
                        pageNumber=page.pageNumber
                    )
                    all_elements.append(elem)
                    markdown_lines.append(f"\n![Schéma {elem_counter}](data:image/png;base64,{clean_b64})\n")
                    elem_counter += 1
                    continue

                # 2. Inférence HTR sur le texte avec mots et alternatives (P4 / ML-3)
                chain, _ = registry.chain_for(lang)
                eng_name = chain[0] if chain else "trocr_fr"
                engine = registry.get(eng_name)
                lines_out = engine.recognize_lines([pil_crop], num_beams=1, with_words=True)
                line_out = lines_out[0] if lines_out else None

                if line_out:
                    line_out = postprocess_line(line_out, lang=lang, user_subs=None)
                    text_strip = line_out.text.strip()
                    confidence = line_out.confidence
                    min_word_conf = line_out.min_word_confidence
                    words_pydantic = [
                        WordResult(
                            index=w.index,
                            text=w.text,
                            confidence=w.confidence,
                            alternatives=w.alternatives,
                            bbox=w.bbox,
                            corrected=w.corrected,
                            original=w.original,
                            source="model",
                        )
                        for w in line_out.words
                    ]
                    alternatives = line_out.alternatives
                else:
                    text_strip = ""
                    confidence = 0.0
                    min_word_conf = 0.0
                    words_pydantic = []
                    alternatives = []

                webp_thumb = pil_to_webp_thumbnail(pil_crop)
                fp_val = stroke_fingerprint(group_strokes)

                elem = StructuralElement(
                    id=elem_counter,
                    type=explicit_type or "paragraph",
                    text=text_strip,
                    confidence=confidence,
                    calibrated=False,
                    min_word_confidence=min_word_conf,
                    words=words_pydantic,
                    alternatives=alternatives,
                    thumbnail=webp_thumb,
                    bbox=bbox,
                    image_base64=clean_b64,
                    stroke_ids=stroke_ids,
                    pageNumber=page.pageNumber,
                    source="model",
                    stroke_fingerprint=fp_val,
                )

                # Appliquer la couche de correction (mémoire de ligne → dictionnaire) EN DERNIER
                elem = correction_layer.apply(
                    user_id=user_id,
                    lang=lang,
                    strokes=group_strokes,
                    result=elem,
                    user_subs=user_subs,
                )
                text_strip = elem.text.strip()
                if not text_strip:
                    continue

                # 3. Détermination du type d'élément (Explicit > Heuristiques)
                if explicit_type:
                    elem_type = explicit_type
                else:
                    elem_type = "paragraph"
                    is_first_line = (idx == 1) or (top_y < canvas_h * 0.20)
                    is_roman = bool(self.ROMAN_REGEX.match(text_strip))
                    is_subtitle = bool(self.SUBTITLE_REGEX.match(text_strip))
                    is_centered = abs(center_x - (canvas_w / 2.0)) < (canvas_w * 0.3)
                    is_large = height > 1.25 * median_height

                    if is_first_line or is_roman or (is_large and is_centered) or text_strip.lower().startswith("titre"):
                        elem_type = "h1"
                    elif is_subtitle or (is_large and not is_centered) or text_strip.lower().startswith("chapitre"):
                        elem_type = "h2"
                    else:
                        elem_type = "paragraph"

                elem.type = elem_type

                # Mise à jour du Markdown
                if elem_type.startswith("h") and len(elem_type) == 2 and elem_type[1].isdigit():
                    level = int(elem_type[1])
                    hashes = "#" * level
                    markdown_lines.append(f"\n{hashes} {text_strip}\n")
                else:
                    markdown_lines.append(text_strip)

                all_elements.append(elem)
                elem_counter += 1

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        full_markdown = "\n".join(markdown_lines)

        return StructuralHTRResponse(
            success=True,
            processingTimeMs=elapsed_ms,
            subject=request.subject or "Cours Manuscrit",
            lessonTitle=request.lessonTitle or "Nouveau Cours",
            elements=all_elements,
            fullMarkdown=full_markdown
        )

structural_htr_service = StructuralHTRService()
