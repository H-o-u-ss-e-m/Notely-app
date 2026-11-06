"""
Routes API — Espace personnel et RGPD (SEC-8 / §4.5, §5.4).
GET    /api/v1/me/settings  → consulter consentements et préférences
PUT    /api/v1/me/settings  → mettre à jour consentements (consent_train, consent_cloud_ocr)
GET    /api/v1/me/export    → droit d'accès / portabilité (export JSON complet de ses cours & corrections)
DELETE /api/v1/me           → droit à l'effacement (suppression de compte en cascade + journalisation)
"""
import io
import json
import uuid
import zipfile
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.user_settings import UserSettings
from app.db.models.user_dictionary import UserDictionary
from app.db.models.ocr_correction import OcrCorrection
from app.db.models.course import Subject, Lesson, NotebookPage, Stroke
from app.db.models.audit_log import AuditLog
from app.schemas.ocr_feedback import UserSettingsResponse, UserSettingsUpdateRequest
from app.core.security import extract_user_id_from_header

logger = logging.getLogger("me_rgpd")
router = APIRouter()


def _require_user(authorization: Optional[str], db: Session) -> User:
    """Retourne l'utilisateur authentifié ou lève 401/404."""
    user_id = extract_user_id_from_header(authorization)
    if not user_id or user_id == "usr-guest":
        raise HTTPException(
            status_code=401,
            detail="Authentification requise.",
        )
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Identifiant utilisateur invalide.")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    return user


def _log_audit_event(
    db: Session,
    event: str,
    user_id: Optional[uuid.UUID] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Enregistre un événement dans la table audit_logs (sans contenu manuscrit)."""
    ip_addr = request.client.host if request and request.client else None
    audit = AuditLog(
        user_id=user_id,
        event=event,
        metadata_json=metadata_json,
        ip_address=ip_addr,
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()
    return audit


@router.get("/me/settings", response_model=UserSettingsResponse, tags=["RGPD & Profil"])
async def get_my_settings(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Retourne les consentements RGPD et les préférences de l'utilisateur."""
    user = _require_user(authorization, db)
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    if not settings:
        settings = UserSettings(
            user_id=user.id,
            consent_train=False,
            consent_cloud_ocr=False,
            ocr_language="fr",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return UserSettingsResponse(
        user_id=str(settings.user_id),
        consent_train=settings.consent_train,
        consent_cloud_ocr=settings.consent_cloud_ocr,
        consent_withdrawn_at=settings.consent_withdrawn_at.isoformat() if settings.consent_withdrawn_at else None,
        ocr_language=settings.ocr_language,
        updated_at=settings.updated_at.isoformat(),
    )


@router.put("/me/settings", response_model=UserSettingsResponse, tags=["RGPD & Profil"])
async def update_my_settings(
    body: UserSettingsUpdateRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Met à jour les consentements IA et préférences.
    En cas de retrait du consentement d'entraînement, marque automatiquement
    consent_withdrawn_at sur les corrections et journalise l'action (SEC-8).
    """
    user = _require_user(authorization, db)
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    if not settings:
        settings = UserSettings(
            user_id=user.id,
            consent_train=False,
            consent_cloud_ocr=False,
            ocr_language="fr",
        )
        db.add(settings)

    now = datetime.utcnow()
    changes = {}

    if body.consent_train is not None and body.consent_train != settings.consent_train:
        changes["consent_train_old"] = settings.consent_train
        changes["consent_train_new"] = body.consent_train
        settings.consent_train = body.consent_train
        if not body.consent_train:
            # Retrait du consentement : marquer date de retrait
            settings.consent_withdrawn_at = now
            # Propager sur les corrections existantes pour exclusion des exports ML
            db.query(OcrCorrection).filter(OcrCorrection.user_id == user.id).update(
                {"consent_withdrawn_at": now, "consent_train": False}
            )

    if body.consent_cloud_ocr is not None:
        changes["consent_cloud_ocr"] = body.consent_cloud_ocr
        settings.consent_cloud_ocr = body.consent_cloud_ocr

    if body.ocr_language is not None:
        settings.ocr_language = body.ocr_language

    settings.updated_at = now
    db.commit()
    db.refresh(settings)

    if changes:
        _log_audit_event(
            db,
            event="consent_change",
            user_id=user.id,
            metadata_json=changes,
            request=request,
        )

    return UserSettingsResponse(
        user_id=str(settings.user_id),
        consent_train=settings.consent_train,
        consent_cloud_ocr=settings.consent_cloud_ocr,
        consent_withdrawn_at=settings.consent_withdrawn_at.isoformat() if settings.consent_withdrawn_at else None,
        ocr_language=settings.ocr_language,
        updated_at=settings.updated_at.isoformat(),
    )


@router.get("/me/export", tags=["RGPD & Profil"])
async def export_my_data(
    format: str = Query("zip", description="Format d'export : 'zip' (archive conforme §4.8) ou 'json'"),
    request: Request = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Droit à la portabilité (RGPD Art. 20 / §4.8) :
    Exporte l'intégralité des données personnelles de l'utilisateur sous forme d'archive ZIP
    (profil, espaces, cours, pages, tracés vectoriels, corrections et dictionnaire personnel).
    Supporte également le format JSON brut via ?format=json.
    """
    user = _require_user(authorization, db)

    # Récupérer les données de cours
    subjects = db.query(Subject).filter(Subject.user_id == user.id).all()
    subjects_data = []
    for s in subjects:
        lessons_data = []
        for l in s.lessons:
            pages_data = []
            for p in l.pages:
                strokes_data = [
                    {
                        "id": str(st.id),
                        "tool": st.tool,
                        "color": st.color,
                        "width": st.width,
                        "points": st.points,
                        "bbox": st.bbox,
                    }
                    for st in p.strokes
                ]
                pages_data.append({
                    "id": str(p.id),
                    "page_number": p.page_number,
                    "width": p.width,
                    "height": p.height,
                    "strokes": strokes_data,
                })
            lessons_data.append({
                "id": str(l.id),
                "title": l.title,
                "version": l.version,
                "created_at": l.created_at.isoformat(),
                "pages": pages_data,
            })
        subjects_data.append({
            "id": str(s.id),
            "name": s.name,
            "color": s.color,
            "description": s.description,
            "lessons": lessons_data,
        })

    # Récupérer les corrections et le dictionnaire
    corrections = db.query(OcrCorrection).filter(OcrCorrection.user_id == user.id).all()
    corrections_data = [
        {
            "id": str(c.id),
            "predicted_text": c.predicted_text,
            "corrected_text": c.corrected_text,
            "language": c.language,
            "confidence": c.confidence,
            "scope": getattr(c, "scope", "line"),
            "created_at": c.created_at.isoformat(),
        }
        for c in corrections
    ]

    dict_entries = db.query(UserDictionary).filter(UserDictionary.user_id == user.id).all()
    dictionary_data = [
        {
            "language": d.language,
            "wrong": d.wrong,
            "right": d.right,
            "count": d.count,
        }
        for d in dict_entries
    ]

    export_payload = {
        "export_date": datetime.utcnow().isoformat(),
        "format_version": "1.0",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else datetime.utcnow().isoformat(),
        },
        "subjects": subjects_data,
        "ocr_corrections": corrections_data,
        "user_dictionary": dictionary_data,
    }

    _log_audit_event(
        db,
        event="export",
        user_id=user.id,
        metadata_json={
            "format": format,
            "subjects_count": len(subjects_data),
            "corrections_count": len(corrections_data),
        },
        request=request,
    )

    if format == "json":
        return export_payload

    # Génération de l'archive ZIP conforme §4.8
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("profile.json", json.dumps(export_payload["user"], indent=2, ensure_ascii=False))
        zf.writestr("courses.json", json.dumps(subjects_data, indent=2, ensure_ascii=False))
        zf.writestr("ocr_corrections.json", json.dumps(corrections_data, indent=2, ensure_ascii=False))
        zf.writestr("user_dictionary.json", json.dumps(dictionary_data, indent=2, ensure_ascii=False))
        zf.writestr("export_metadata.json", json.dumps({
            "export_date": export_payload["export_date"],
            "format_version": export_payload["format_version"],
            "user_id": str(user.id),
        }, indent=2, ensure_ascii=False))

    zip_bytes = zip_buffer.getvalue()
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=notely_export_{user.id}.zip"
        },
    )


@router.delete("/me", tags=["RGPD & Profil"])
async def delete_my_account(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Droit à l'effacement (RGPD Art. 17) :
    Supprime définitivement le compte utilisateur et cascade sur toutes ses données
    (cours, leçons, pages, tracés, corrections, dictionnaires, jobs, sessions).
    Enregistre un log d'audit anonymisé avant destruction (SEC-8).
    """
    user = _require_user(authorization, db)
    user_id_copy = user.id

    # Journal d'audit (sans user_id persistant pour respecter le droit à l'oubli)
    _log_audit_event(
        db,
        event="delete_account",
        user_id=None,
        metadata_json={"deleted_user_email_hash": str(hash(user.email))},
        request=request,
    )

    db.delete(user)
    db.commit()

    logger.info(f"Compte utilisateur supprimé avec succès : {user_id_copy}")
    return {
        "success": True,
        "message": "Votre compte et l'ensemble de vos données associées ont été supprimés conformément au RGPD.",
    }
