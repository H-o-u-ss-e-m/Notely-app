"""
Routes API — Feedback et corrections OCR utilisateur (ML-5, DB-4, SEC-8 / §8.5, §8.6).
POST   /api/v1/ocr/feedback          → enregistrer une correction (mot ou ligne) avec filtres anti-poison
GET    /api/v1/ocr/corrections        → lister ses corrections (paginé, anti-IDOR)
DELETE /api/v1/ocr/corrections/{id}  → supprimer une correction (droit à l'oubli RGPD)
GET    /api/v1/ocr/dictionary         → lister son dictionnaire personnel
DELETE /api/v1/ocr/dictionary/{id}   → supprimer une entrée du dictionnaire personnel
"""
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.ocr_correction import OcrCorrection
from app.db.models.user_settings import UserSettings
from app.db.models.user_dictionary import UserDictionary
from app.schemas.ocr_feedback import (
    OcrFeedbackRequest,
    OcrFeedbackResponse,
    OcrCorrectionItem,
    OcrCorrectionsListResponse,
    UserDictionaryItem,
    UserDictionaryListResponse,
)
from app.core.security import extract_user_id_from_header
from app.domain.anti_poison import validate_correction
from app.domain.line_memory import line_memory
from app.domain.user_dictionary import bump_user_dictionary

logger = logging.getLogger("ocr_feedback")
router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_user_id(authorization: Optional[str]) -> str:
    """
    Retourne le user_id ou lève 401 si non authentifié.
    Les corrections sont liées à un utilisateur réel (pas 'usr-guest').
    """
    user_id = extract_user_id_from_header(authorization)
    if not user_id or user_id == "usr-guest":
        raise HTTPException(
            status_code=401,
            detail="Authentification requise pour enregistrer une correction OCR.",
        )
    return user_id


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/ocr/feedback", response_model=OcrFeedbackResponse, tags=["OCR Feedback"])
async def submit_ocr_correction(
    request: OcrFeedbackRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Enregistre une correction OCR validée par l'utilisateur (mot ou ligne).
    Applique le filtre anti-poison (§8.6.b), vérifie le consentement serveur (SEC-8),
    incrémente le dictionnaire personnel (ML-5) et met en cache la mémoire de lignes.
    """
    user_id = _require_user_id(authorization)
    lang = (request.language or "fr").lower().strip()

    # 1. Validation anti-poison consciente du moteur et de la langue (§8.6.b & Plan v2 §1.5)
    is_valid, reason, err_code = validate_correction(
        predicted_text=request.predicted_text,
        corrected_text=request.corrected_text,
        max_cer=0.6,
        max_len=300,
        lang=lang,
        confidence=request.confidence,
        return_code=True,
    )
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=f"Correction non enregistrée ({err_code}) : {reason}",
        )

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"user_id invalide : {user_id}")

    # 2. Vérification du consentement serveur pour l'entraînement global (SEC-8)
    #    Note (Plan v2 §1.7) : Si consent_train=False, la correction fonctionne quand même
    #    pour la mémoire personnelle de l'utilisateur, mais n'entre pas dans l'entraînement global.
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == user_uuid).first()
    server_consent_train = user_settings.consent_train if user_settings else False
    effective_consent_train = bool(request.consent_train and server_consent_train)

    strokes_data = None
    if effective_consent_train and request.strokes:
        try:
            strokes_data = [
                s.model_dump() if hasattr(s, "model_dump") else s
                for s in request.strokes
            ]
        except Exception:
            strokes_data = None

    page_uuid = None
    if request.page_id:
        try:
            page_uuid = uuid.UUID(request.page_id)
        except ValueError:
            page_uuid = None

    # Calcul automatique de stroke_fingerprint et ink_hash (Plan v2 §1.3, §1.4)
    from app.ml.cache import stroke_fingerprint as calc_fp
    from app.domain.correction_layer import ink_hash_hex, normalize_key

    source_strokes = request.strokes or []
    if not source_strokes and page_uuid and request.stroke_ids:
        try:
            from app.db.models.course import Stroke as DbStroke
            db_strokes = (
                db.query(DbStroke)
                .filter(DbStroke.page_id == page_uuid, DbStroke.id.in_(request.stroke_ids))
                .all()
            )
            source_strokes = [
                {"id": s.id, "points": s.points or [], "startTime": s.start_time, "tool": s.tool}
                for s in db_strokes
            ]
        except Exception:
            source_strokes = []

    fp = request.stroke_fingerprint
    if not fp and source_strokes:
        try:
            fp = calc_fp(source_strokes)
        except Exception:
            fp = None

    ih_val = None
    if source_strokes:
        try:
            ih_val = ink_hash_hex(source_strokes)
        except Exception:
            ih_val = None

    # 3. Création de l'enregistrement de correction
    correction = OcrCorrection(
        user_id=user_uuid,
        page_id=page_uuid,
        scope=request.scope or "line",
        word_index=request.word_index,
        stroke_fingerprint=fp,
        ink_hash=ih_val,
        stroke_ids=request.stroke_ids or [],
        strokes_json=strokes_data,
        engine=request.engine,
        language=lang,
        predicted_text=request.predicted_text,
        corrected_text=request.corrected_text,
        line_predicted=request.line_predicted,
        line_corrected=request.line_corrected,
        alternatives=request.alternatives,
        confidence=request.confidence,
        consent_train=effective_consent_train,
        source=request.source or "manual",
    )

    db.add(correction)
    db.commit()
    db.refresh(correction)

    # 4. Mise à jour du dictionnaire personnel (dès la 1re correction, Plan v2 §1.3)
    norm_wrong = normalize_key(request.predicted_text, lang)
    existing_dict = (
        db.query(UserDictionary)
        .filter(
            UserDictionary.user_id == user_uuid,
            UserDictionary.language == lang,
            UserDictionary.wrong == norm_wrong,
        )
        .first()
    )
    if existing_dict is not None:
        try:
            from app.core.metrics import metrics_collector
            metrics_collector.record_repeat_error(lang)
        except Exception:
            pass

    bump_user_dictionary(
        db=db,
        user_id=user_uuid,
        language=lang,
        wrong=request.predicted_text,
        right=request.corrected_text,
    )

    # 5. Mémoire de lignes exacte + tolérante ink_hash (§8.5.c & Plan v2 §1.3, §1.4)
    text_to_remember = request.line_corrected or request.corrected_text
    if text_to_remember and (fp or ih_val):
        line_memory.store(
            user_id=str(user_uuid),
            stroke_fingerprint=fp or "",
            line_corrected=text_to_remember,
            ink_hash_val=ih_val,
            lang=lang,
        )

    logger.info(f"Correction OCR enregistrée : {correction.id} (user={user_id}, train={effective_consent_train})")

    # MLOps §9.3 : Enregistrement de la métrique de correction
    try:
        from app.core.metrics import metrics_collector
        metrics_collector.record_correction(language=request.language, engine=request.engine)
    except Exception:
        pass

    return OcrFeedbackResponse(
        success=True,
        correction_id=str(correction.id),
        message="Correction enregistrée avec succès.",
    )


@router.get("/ocr/corrections", response_model=OcrCorrectionsListResponse, tags=["OCR Feedback"])
async def list_my_corrections(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Retourne les corrections OCR de l'utilisateur connecté (paginées, anti-IDOR)."""
    user_id = _require_user_id(authorization)

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"user_id invalide : {user_id}")

    corrections = (
        db.query(OcrCorrection)
        .filter(OcrCorrection.user_id == user_uuid)
        .order_by(OcrCorrection.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    total = (
        db.query(OcrCorrection)
        .filter(OcrCorrection.user_id == user_uuid)
        .count()
    )

    items = [
        OcrCorrectionItem(
            id=str(c.id),
            predicted_text=c.predicted_text,
            corrected_text=c.corrected_text,
            scope=getattr(c, "scope", "line") or "line",
            word_index=getattr(c, "word_index", None),
            language=c.language,
            engine=c.engine,
            confidence=c.confidence,
            consent_train=c.consent_train,
            source=getattr(c, "source", "manual") or "manual",
            created_at=c.created_at.isoformat(),
        )
        for c in corrections
    ]

    return OcrCorrectionsListResponse(corrections=items, total=total)


@router.delete(
    "/ocr/corrections/{correction_id}",
    tags=["OCR Feedback"],
    summary="Supprimer une correction (droit à l'oubli RGPD)",
)
async def delete_correction(
    correction_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Supprime une correction OCR appartenant à l'utilisateur.
    Conforme au droit à l'effacement (RGPD Art. 17).
    """
    user_id = _require_user_id(authorization)

    try:
        cid = uuid.UUID(correction_id)
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID invalide.")

    correction = (
        db.query(OcrCorrection)
        .filter(OcrCorrection.id == cid, OcrCorrection.user_id == user_uuid)
        .first()
    )
    if not correction:
        raise HTTPException(status_code=404, detail="Correction introuvable ou accès refusé.")

    db.delete(correction)
    db.commit()
    return {"success": True, "message": "Correction supprimée."}


@router.get("/ocr/dictionary", response_model=UserDictionaryListResponse, tags=["OCR Feedback"])
async def list_user_dictionary(
    language: str = Query("fr"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Retourne la liste des règles de substitution du dictionnaire personnel."""
    user_id = _require_user_id(authorization)
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id invalide.")

    entries = (
        db.query(UserDictionary)
        .filter(UserDictionary.user_id == user_uuid, UserDictionary.language == language)
        .order_by(UserDictionary.count.desc())
        .limit(200)
        .all()
    )

    items = [
        UserDictionaryItem(
            id=str(e.id),
            language=e.language,
            wrong=e.wrong,
            right=e.right,
            count=e.count,
            last_seen=e.last_seen.isoformat(),
        )
        for e in entries
    ]
    return UserDictionaryListResponse(items=items, total=len(items))


@router.delete("/ocr/dictionary/{entry_id}", tags=["OCR Feedback"])
async def delete_dictionary_entry(
    entry_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Supprime une entrée du dictionnaire personnel."""
    user_id = _require_user_id(authorization)
    try:
        eid = uuid.UUID(entry_id)
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID invalide.")

    entry = (
        db.query(UserDictionary)
        .filter(UserDictionary.id == eid, UserDictionary.user_id == user_uuid)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entrée introuvable ou accès refusé.")

    db.delete(entry)
    db.commit()
    return {"success": True, "message": "Entrée de dictionnaire supprimée."}
