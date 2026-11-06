"""
CourseService — Logique métier pour Matières, Cours, Pages et Tracés.
Toutes les opérations vérifient l'appartenance à l'utilisateur authentifié.
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.courses.repository import subject_repository, lesson_repository, page_repository
from app.db.models.course import Subject, Lesson, NotebookPage
from app.schemas.courses import (
    SubjectCreateDTO, SubjectUpdateDTO, SubjectEntity,
    LessonCreateDTO, LessonUpdateDTO, LessonEntity,
    NotebookPageDTO, StrokeDTO, PointDTO, BoundingBoxDTO
)

logger = logging.getLogger(__name__)


def _stroke_to_dto(stroke) -> StrokeDTO:
    bbox = None
    if stroke.bbox:
        bbox = BoundingBoxDTO(**stroke.bbox)
    points = [PointDTO(**p) for p in (stroke.points or [])]
    cid = getattr(stroke, "client_id", None)
    stroke_id = cid if (isinstance(cid, str) and cid) else str(stroke.id)
    return StrokeDTO(
        id=stroke_id,
        points=points,
        startTime=stroke.start_time,
        endTime=stroke.end_time,
        color=stroke.color,
        width=stroke.width,
        tool=stroke.tool,
        contentType=stroke.content_type,
        pointerType="touch",
        bbox=bbox,
    )


def _page_to_dto(page: NotebookPage) -> NotebookPageDTO:
    active_strokes = [
        s for s in (page.strokes or [])
        if getattr(s, "deleted_at", None) is None
    ]
    active_strokes.sort(key=lambda s: (getattr(s, "seq", 0) or 0, getattr(s, "start_time", 0.0) or 0.0))
    return NotebookPageDTO(
        id=str(page.id),
        pageNumber=page.page_number,
        strokes=[_stroke_to_dto(s) for s in active_strokes],
        redoStack=[],
        width=page.width,
        height=page.height,
    )


def _lesson_to_entity(lesson: Lesson) -> LessonEntity:
    pages = [_page_to_dto(p) for p in (lesson.pages or [])]
    return LessonEntity(
        id=str(lesson.id),
        subjectId=str(lesson.subject_id),
        title=lesson.title,
        updatedAt=lesson.updated_at.strftime("%Y-%m-%d %H:%M") if lesson.updated_at else "",
        pageCount=len(pages),
        version=lesson.version,
        pages=pages,
    )


def _subject_to_entity(subject: Subject) -> SubjectEntity:
    active_lessons = [
        l for l in (subject.lessons or [])
        if getattr(l, "deleted_at", None) is None
    ]
    return SubjectEntity(
        id=str(subject.id),
        name=subject.name,
        color=subject.color,
        description=subject.description or "",
        lessons=[_lesson_to_entity(l) for l in active_lessons],
        createdAt=subject.created_at.strftime("%Y-%m-%d") if subject.created_at else "",
    )


class CourseService:

    # ── Matières ────────────────────────────────────────────────────────────

    def list_subjects(self, db: Session, user_id: str) -> List[SubjectEntity]:
        subjects = subject_repository.list_for_user(db, user_id)
        return [_subject_to_entity(s) for s in subjects]

    def get_subject(self, db: Session, subject_id: str, user_id: str) -> Optional[SubjectEntity]:
        subj = subject_repository.get(db, subject_id, user_id)
        return _subject_to_entity(subj) if subj else None

    def create_subject(self, db: Session, dto: SubjectCreateDTO, user_id: str) -> SubjectEntity:
        subj = subject_repository.create(
            db, user_id=user_id,
            name=dto.name, color=dto.color or "#1E40AF",
            description=dto.description or ""
        )
        return _subject_to_entity(subj)

    def update_subject(self, db: Session, subject_id: str, dto: SubjectUpdateDTO, user_id: str) -> Optional[SubjectEntity]:
        subj = subject_repository.get(db, subject_id, user_id)
        if not subj:
            return None
        subject_repository.update(
            db, subj,
            name=dto.name, color=dto.color, description=dto.description
        )
        return _subject_to_entity(subj)

    def delete_subject(self, db: Session, subject_id: str, user_id: str) -> bool:
        subj = subject_repository.get(db, subject_id, user_id)
        if not subj:
            return False
        subject_repository.delete(db, subj)
        return True

    # ── Cours ────────────────────────────────────────────────────────────────

    def get_lesson(self, db: Session, lesson_id: str, user_id: str) -> Optional[LessonEntity]:
        lesson = lesson_repository.get(db, lesson_id, user_id)
        return _lesson_to_entity(lesson) if lesson else None

    def create_lesson(self, db: Session, dto: LessonCreateDTO, user_id: str) -> Optional[LessonEntity]:
        # Vérifier que le sujet appartient à l'utilisateur
        subj = subject_repository.get(db, dto.subjectId, user_id)
        if not subj:
            return None
        lesson = lesson_repository.create(db, subject_id=dto.subjectId, title=dto.title)
        return _lesson_to_entity(lesson)

    def update_lesson(self, db: Session, lesson_id: str, dto: LessonUpdateDTO, user_id: str) -> Optional[LessonEntity]:
        lesson = lesson_repository.get(db, lesson_id, user_id)
        if not lesson:
            return None

        # Mise à jour du titre si fourni
        if dto.title is not None:
            lesson_repository.update(db, lesson, title=dto.title)

        # Fusion atomique des pages et tracés
        if dto.pages is not None:
            self._sync_pages(db, lesson, dto.pages)

        return _lesson_to_entity(lesson)

    def delete_lesson(self, db: Session, lesson_id: str, user_id: str) -> bool:
        lesson = lesson_repository.get(db, lesson_id, user_id)
        if not lesson:
            return False
        lesson_repository.delete(db, lesson)
        return True

    def _sync_pages(self, db: Session, lesson: Lesson, pages_dto: list):
        """
        Synchronise les pages et tracés d'un cours.
        Fusion atomique : les tracés existants sont préservés et fusionnés.
        """
        existing_pages = {str(p.id): p for p in lesson.pages}

        for pdata in pages_dto:
            page_id = pdata.id
            strokes_raw = [s.dict() if hasattr(s, 'dict') else s for s in (pdata.strokes or [])]

            # Convertir les strokeDTO en dict compatibles avec le repository
            strokes_for_repo = []
            for s in strokes_raw:
                strokes_for_repo.append({
                    "id": s.get("id") if isinstance(s, dict) else s.id,
                    "points": [p.dict() if hasattr(p, 'dict') else p for p in (s.get("points", []) if isinstance(s, dict) else s.points)],
                    "color": s.get("color", "#000000") if isinstance(s, dict) else s.color,
                    "width": s.get("width", 3.0) if isinstance(s, dict) else s.width,
                    "tool": s.get("tool", "pen") if isinstance(s, dict) else s.tool,
                    "contentType": s.get("contentType", "normal") if isinstance(s, dict) else s.contentType,
                    "bbox": s.get("bbox") if isinstance(s, dict) else (s.bbox.dict() if s.bbox else None),
                    "startTime": s.get("startTime", 0.0) if isinstance(s, dict) else s.startTime,
                    "endTime": s.get("endTime", 0.0) if isinstance(s, dict) else s.endTime,
                })

            if page_id in existing_pages:
                page_repository.save_strokes(db, existing_pages[page_id], strokes_for_repo)
            else:
                # Nouvelle page
                new_page = NotebookPage(
                    lesson_id=lesson.id,
                    page_number=pdata.pageNumber,
                    width=pdata.width or 794.0,
                    height=pdata.height or 1123.0,
                )
                db.add(new_page)
                db.flush()
                page_repository.save_strokes(db, new_page, strokes_for_repo)


course_service = CourseService()
