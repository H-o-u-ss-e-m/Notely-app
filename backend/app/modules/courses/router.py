"""
Routeur Courses — /api/v1/courses/*
Utilise PostgreSQL via CourseService et les dépendances anti-IDOR `get_owned_*` (SEC-4 / SEC-6).
"""
from typing import List
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.course import Subject, Lesson, NotebookPage
from app.api.deps import current_user_id, get_owned_subject, get_owned_lesson, get_owned_page
from app.core.ratelimit import limiter
from app.schemas.courses import (
    SubjectEntity, SubjectCreateDTO, SubjectUpdateDTO,
    LessonEntity, LessonCreateDTO, LessonUpdateDTO,
    StrokeDeltaDTO, PageStrokesResponseDTO,
)
from app.schemas.structural import PDFRawExportRequest, StructuralHTRRequest
from app.modules.courses.service import course_service, _subject_to_entity, _lesson_to_entity, _stroke_to_dto
from app.modules.courses.repository import StrokeIdConflict, page_repository
from app.services.pdf_raw_generator import pdf_raw_generator_service
from app.services.pdf_generator_service import pdf_generator_service
from app.services.structural_htr_service import structural_htr_service

router = APIRouter()


# ── Matières ────────────────────────────────────────────────────────────────

@router.get("/courses/subjects", response_model=List[SubjectEntity])
async def get_all_subjects(user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    return course_service.list_subjects(db, user_id)


@router.get("/courses/subjects/{subject_id}", response_model=SubjectEntity)
async def get_subject(subj: Subject = Depends(get_owned_subject)):
    return _subject_to_entity(subj)


@router.post("/courses/subjects", response_model=SubjectEntity, status_code=201)
async def create_subject(dto: SubjectCreateDTO, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    return course_service.create_subject(db, dto, user_id)


@router.put("/courses/subjects/{subject_id}", response_model=SubjectEntity)
async def update_subject(
    dto: SubjectUpdateDTO,
    subj: Subject = Depends(get_owned_subject),
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    updated = course_service.update_subject(db, str(subj.id), dto, user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Matière introuvable")
    return updated


@router.delete("/courses/subjects/{subject_id}", status_code=204)
async def delete_subject(
    subj: Subject = Depends(get_owned_subject),
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    if not course_service.delete_subject(db, str(subj.id), user_id):
        raise HTTPException(status_code=404, detail="Matière introuvable")
    return None


# ── Cours ────────────────────────────────────────────────────────────────────

@router.post("/courses/lessons", response_model=LessonEntity, status_code=201)
async def create_lesson(dto: LessonCreateDTO, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    lesson = course_service.create_lesson(db, dto, user_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Matière de rattachement introuvable")
    return lesson


@router.get("/courses/subjects/{subject_id}/lessons/{lesson_id}", response_model=LessonEntity)
async def get_lesson(
    subj: Subject = Depends(get_owned_subject),
    lesson: Lesson = Depends(get_owned_lesson),
):
    if lesson.subject_id != subj.id:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    return _lesson_to_entity(lesson)


@router.put("/courses/subjects/{subject_id}/lessons/{lesson_id}", response_model=LessonEntity)
async def update_lesson(
    dto: LessonUpdateDTO,
    subj: Subject = Depends(get_owned_subject),
    lesson: Lesson = Depends(get_owned_lesson),
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    if lesson.subject_id != subj.id:
        raise HTTPException(status_code=404, detail="Cours ou matière introuvable")
    try:
        updated = course_service.update_lesson(db, str(lesson.id), dto, user_id)
    except StrokeIdConflict as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail="Cours ou matière introuvable")
    return updated


@router.delete("/courses/subjects/{subject_id}/lessons/{lesson_id}", status_code=204)
async def delete_lesson(
    subj: Subject = Depends(get_owned_subject),
    lesson: Lesson = Depends(get_owned_lesson),
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    if lesson.subject_id != subj.id:
        raise HTTPException(status_code=404, detail="Cours ou matière introuvable")
    if not course_service.delete_lesson(db, str(lesson.id), user_id):
        raise HTTPException(status_code=404, detail="Cours ou matière introuvable")
    return None


# ── Export PDF ──────────────────────────────────────────────────────────────

@router.post("/courses/subjects/{subject_id}/lessons/{lesson_id}/export/pdf-raw")
@limiter.limit("5/minute")
async def export_pdf_raw(
    request: Request,
    subj: Subject = Depends(get_owned_subject),
    lesson: Lesson = Depends(get_owned_lesson),
):
    if lesson.subject_id != subj.id:
        raise HTTPException(status_code=404, detail="Cours ou matière introuvable")
    lesson_dto = _lesson_to_entity(lesson)
    raw_req = PDFRawExportRequest(
        subject=subj.name,
        lessonTitle=lesson.title,
        pages=[p.dict() for p in lesson_dto.pages] if lesson_dto.pages else []
    )
    pdf_bytes = pdf_raw_generator_service.generate_raw_pdf_bytes(raw_req)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{subj.name}_{lesson.title}_Original.pdf"'})


@router.post("/courses/subjects/{subject_id}/lessons/{lesson_id}/export/pdf-ai")
@limiter.limit("5/minute")
async def export_pdf_ai(
    request: Request,
    subj: Subject = Depends(get_owned_subject),
    lesson: Lesson = Depends(get_owned_lesson),
    user_id: str = Depends(current_user_id),
):
    if lesson.subject_id != subj.id:
        raise HTTPException(status_code=404, detail="Cours ou matière introuvable")
    lesson_dto = _lesson_to_entity(lesson)
    htr_req = StructuralHTRRequest(
        pages=[p.dict() for p in lesson_dto.pages] if lesson_dto.pages else [],
        subject=subj.name,
        lessonTitle=lesson.title
    )
    htr_res = structural_htr_service.process_structural_strokes(htr_req, user_id=str(user_id))
    pdf_bytes = pdf_generator_service.generate_pdf_bytes(htr_res)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{subj.name}_{lesson.title}_AI.pdf"'})


# ── Synchronisation différentielle & Chargement paresseux des tracés (DB-3 / §5.7) ──

@router.patch("/pages/{page_id}/strokes")
@router.patch("/courses/pages/{page_id}/strokes")
async def patch_strokes(
    delta: StrokeDeltaDTO,
    page: NotebookPage = Depends(get_owned_page),
    db: Session = Depends(get_db),
):
    if delta.baseVersion != page.version:
        raise HTTPException(
            status_code=409,
            detail={"code": "version_mismatch", "serverVersion": page.version},
        )
    added_for_repo = [
        {
            "id": s.id,
            "points": [p.dict() if hasattr(p, "dict") else p for p in (s.points or [])],
            "color": s.color or "#000000",
            "width": s.width or 3.0,
            "tool": s.tool or "pen",
            "contentType": s.contentType or "normal",
            "bbox": s.bbox.dict() if s.bbox else None,
            "startTime": s.startTime,
            "endTime": s.endTime,
        }
        for s in delta.added
    ]
    updated_page = page_repository.patch_strokes_delta(
        db, page, added=added_for_repo, removed_client_ids=delta.removedClientIds
    )
    return {"pageId": str(updated_page.id), "version": updated_page.version}


@router.get("/pages/{page_id}/strokes", response_model=PageStrokesResponseDTO)
@router.get("/courses/pages/{page_id}/strokes", response_model=PageStrokesResponseDTO)
async def get_page_strokes(
    page: NotebookPage = Depends(get_owned_page),
    db: Session = Depends(get_db),
):
    strokes = page_repository.list_active_strokes(db, page.id)
    return PageStrokesResponseDTO(
        pageId=str(page.id),
        version=page.version,
        strokes=[_stroke_to_dto(s) for s in strokes],
    )

