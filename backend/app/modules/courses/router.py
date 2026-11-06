"""
Routeur Courses — /api/v1/courses/*
Utilise PostgreSQL via CourseService. Toutes les routes sont authentifiées.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Response, Header, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.courses import (
    SubjectEntity, SubjectCreateDTO, SubjectUpdateDTO,
    LessonEntity, LessonCreateDTO, LessonUpdateDTO
)
from app.schemas.structural import PDFRawExportRequest, StructuralHTRRequest
from app.modules.courses.service import course_service
from app.modules.courses.repository import StrokeIdConflict
from app.services.pdf_raw_generator import pdf_raw_generator_service
from app.services.pdf_generator_service import pdf_generator_service
from app.services.structural_htr_service import structural_htr_service
from app.core.security import extract_user_id_from_header

router = APIRouter()


def _auth(authorization: Optional[str]) -> str:
    """Extrait le user_id ou lève 401."""
    user_id = extract_user_id_from_header(authorization)
    if user_id == "usr-guest":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")
    return user_id


# ── Matières ────────────────────────────────────────────────────────────────

@router.get("/courses/subjects", response_model=List[SubjectEntity])
async def get_all_subjects(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    return course_service.list_subjects(db, user_id)


@router.get("/courses/subjects/{subject_id}", response_model=SubjectEntity)
async def get_subject(subject_id: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    subj = course_service.get_subject(db, subject_id, user_id)
    if not subj:
        raise HTTPException(status_code=404, detail="Matière introuvable")
    return subj


@router.post("/courses/subjects", response_model=SubjectEntity, status_code=201)
async def create_subject(dto: SubjectCreateDTO, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    return course_service.create_subject(db, dto, user_id)


@router.put("/courses/subjects/{subject_id}", response_model=SubjectEntity)
async def update_subject(subject_id: str, dto: SubjectUpdateDTO, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    subj = course_service.update_subject(db, subject_id, dto, user_id)
    if not subj:
        raise HTTPException(status_code=404, detail="Matière introuvable")
    return subj


@router.delete("/courses/subjects/{subject_id}", status_code=204)
async def delete_subject(subject_id: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    if not course_service.delete_subject(db, subject_id, user_id):
        raise HTTPException(status_code=404, detail="Matière introuvable")
    return None


# ── Cours ────────────────────────────────────────────────────────────────────

@router.post("/courses/lessons", response_model=LessonEntity, status_code=201)
async def create_lesson(dto: LessonCreateDTO, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    lesson = course_service.create_lesson(db, dto, user_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Matière de rattachement introuvable")
    return lesson


@router.get("/courses/subjects/{subject_id}/lessons/{lesson_id}", response_model=LessonEntity)
async def get_lesson(subject_id: str, lesson_id: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    lesson = course_service.get_lesson(db, lesson_id, user_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    return lesson


@router.put("/courses/subjects/{subject_id}/lessons/{lesson_id}", response_model=LessonEntity)
async def update_lesson(subject_id: str, lesson_id: str, dto: LessonUpdateDTO,
                        authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    try:
        lesson = course_service.update_lesson(db, lesson_id, dto, user_id)
    except StrokeIdConflict as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    if not lesson:
        raise HTTPException(status_code=404, detail="Cours ou matière introuvable")
    return lesson


@router.delete("/courses/subjects/{subject_id}/lessons/{lesson_id}", status_code=204)
async def delete_lesson(subject_id: str, lesson_id: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    if not course_service.delete_lesson(db, lesson_id, user_id):
        raise HTTPException(status_code=404, detail="Cours ou matière introuvable")
    return None


# ── Export PDF ──────────────────────────────────────────────────────────────

@router.post("/courses/subjects/{subject_id}/lessons/{lesson_id}/export/pdf-raw")
async def export_pdf_raw(subject_id: str, lesson_id: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    subj = course_service.get_subject(db, subject_id, user_id)
    lesson = course_service.get_lesson(db, lesson_id, user_id)
    if not subj or not lesson:
        raise HTTPException(status_code=404, detail="Cours ou matière introuvable")
    raw_req = PDFRawExportRequest(
        subject=subj.name,
        lessonTitle=lesson.title,
        pages=[p.dict() for p in lesson.pages] if lesson.pages else []
    )
    pdf_bytes = pdf_raw_generator_service.generate_raw_pdf_bytes(raw_req)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{subj.name}_{lesson.title}_Original.pdf"'})


@router.post("/courses/subjects/{subject_id}/lessons/{lesson_id}/export/pdf-ai")
async def export_pdf_ai(subject_id: str, lesson_id: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user_id = _auth(authorization)
    subj = course_service.get_subject(db, subject_id, user_id)
    lesson = course_service.get_lesson(db, lesson_id, user_id)
    if not subj or not lesson:
        raise HTTPException(status_code=404, detail="Cours ou matière introuvable")
    htr_req = StructuralHTRRequest(
        pages=[p.dict() for p in lesson.pages] if lesson.pages else [],
        subject=subj.name,
        lessonTitle=lesson.title
    )
    htr_res = structural_htr_service.process_structural_strokes(htr_req)
    pdf_bytes = pdf_generator_service.generate_pdf_bytes(htr_res)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{subj.name}_{lesson.title}_AI.pdf"'})
