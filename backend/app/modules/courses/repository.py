"""
CourseRepository — Accès PostgreSQL pour Subjects, Lessons, Pages et Strokes.
Toutes les opérations vérifient l'appartenance à l'utilisateur authentifié.
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.db.models.course import Subject, Lesson, NotebookPage, Stroke


class StrokeIdConflict(ValueError):
    """ID de trace deja present sur une autre page (collision ou tentative d'ecrasement)."""


class SubjectRepository:

    def list_for_user(self, db: Session, user_id: str) -> List[Subject]:
        return (
            db.query(Subject)
            .filter(Subject.user_id == user_id)
            .options(
                joinedload(Subject.lessons).joinedload(Lesson.pages).joinedload(NotebookPage.strokes)
            )
            .order_by(Subject.created_at.asc())
            .all()
        )

    def get(self, db: Session, subject_id: str, user_id: str) -> Optional[Subject]:
        return (
            db.query(Subject)
            .filter(Subject.id == subject_id, Subject.user_id == user_id)
            .options(
                joinedload(Subject.lessons).joinedload(Lesson.pages).joinedload(NotebookPage.strokes)
            )
            .first()
        )

    def create(self, db: Session, user_id: str, name: str,
               color: str = "#1E40AF", description: str = "") -> Subject:
        subj = Subject(user_id=user_id, name=name.strip(), color=color, description=description)
        db.add(subj)
        db.flush()
        return subj

    def update(self, db: Session, subject: Subject, **kwargs) -> Subject:
        for k, v in kwargs.items():
            if v is not None:
                setattr(subject, k, v)
        subject.updated_at = datetime.utcnow()
        db.flush()
        return subject

    def delete(self, db: Session, subject: Subject):
        db.delete(subject)
        db.flush()


class LessonRepository:

    def get(self, db: Session, lesson_id: str, user_id: str) -> Optional[Lesson]:
        """Charge un cours en vérifiant l'appartenance à l'utilisateur."""
        return (
            db.query(Lesson)
            .join(Subject)
            .filter(Lesson.id == lesson_id, Subject.user_id == user_id)
            .options(joinedload(Lesson.pages).joinedload(NotebookPage.strokes))
            .first()
        )

    def get_by_subject(self, db: Session, subject_id: str, user_id: str) -> List[Lesson]:
        subj = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user_id).first()
        if not subj:
            return []
        return (
            db.query(Lesson)
            .filter(Lesson.subject_id == subject_id)
            .options(joinedload(Lesson.pages).joinedload(NotebookPage.strokes))
            .order_by(Lesson.created_at.desc())
            .all()
        )

    def create(self, db: Session, subject_id: str, title: str) -> Lesson:
        lesson = Lesson(subject_id=subject_id, title=title.strip())
        db.add(lesson)
        db.flush()

        # Créer la première page automatiquement
        page = NotebookPage(lesson_id=lesson.id, page_number=1)
        db.add(page)
        db.flush()
        return lesson

    def update(self, db: Session, lesson: Lesson, **kwargs) -> Lesson:
        for k, v in kwargs.items():
            if v is not None:
                setattr(lesson, k, v)
        lesson.updated_at = datetime.utcnow()
        lesson.version += 1
        db.flush()
        return lesson

    def delete(self, db: Session, lesson: Lesson):
        db.delete(lesson)
        db.flush()


class PageRepository:

    def get(self, db: Session, page_id: str, user_id: str) -> Optional[NotebookPage]:
        """Charge une page en vérifiant la chaîne page→lesson→subject→user."""
        return (
            db.query(NotebookPage)
            .join(Lesson)
            .join(Subject)
            .filter(NotebookPage.id == page_id, Subject.user_id == user_id)
            .options(joinedload(NotebookPage.strokes))
            .first()
        )

    def save_strokes(self, db: Session, page: NotebookPage, strokes_data: List[dict]) -> NotebookPage:
        """
        Fusion atomique des tracés par ID (Stroke Merge).
        - Les tracés existants sont conservés.
        - Les nouveaux tracés sont ajoutés.
        - Les tracés avec le même ID sont mis à jour.
        """
        existing_ids = {s.id for s in page.strokes}
        incoming_ids = {s["id"] for s in strokes_data if s.get("id")}

        # SECURITE (anti-IDOR) : strokes.id est une PK globale fournie par le client.
        # Un ID deja utilise par une AUTRE page (donc potentiellement un autre
        # utilisateur) ne doit jamais etre ecrase ni reutilise.
        foreign_ids = incoming_ids - existing_ids
        if foreign_ids:
            clash = db.query(Stroke.id).filter(
                Stroke.id.in_(foreign_ids), Stroke.page_id != page.id
            ).first()
            if clash:
                raise StrokeIdConflict("Identifiant de trace deja utilise par une autre page.")

        # Supprimer les tracés qui n'existent plus dans la mise à jour
        # (seulement si le client envoie TOUS ses tracés, pas un diff partiel)
        if strokes_data:  # Ne pas supprimer si le client envoie liste vide
            strokes_to_remove = [s for s in page.strokes if s.id not in incoming_ids]
            for s in strokes_to_remove:
                db.delete(s)

        for sdata in strokes_data:
            stroke_id = sdata.get("id")
            if stroke_id in existing_ids:
                # Mise à jour du tracé existant
                stroke = next(s for s in page.strokes if s.id == stroke_id)
                stroke.points = sdata.get("points", stroke.points)
                stroke.color = sdata.get("color", stroke.color)
                stroke.width = sdata.get("width", stroke.width)
                stroke.tool = sdata.get("tool", stroke.tool)
                stroke.content_type = sdata.get("contentType", stroke.content_type)
                stroke.bbox = sdata.get("bbox", stroke.bbox)
            else:
                # Nouveau tracé
                new_stroke = Stroke(
                    id=stroke_id or f"strk-{uuid.uuid4()}",
                    page_id=page.id,
                    tool=sdata.get("tool", "pen"),
                    content_type=sdata.get("contentType", "normal"),
                    color=sdata.get("color", "#000000"),
                    width=float(sdata.get("width", 3.0)),
                    points=sdata.get("points", []),
                    bbox=sdata.get("bbox"),
                    start_time=float(sdata.get("startTime", 0.0)),
                    end_time=float(sdata.get("endTime", 0.0)),
                )
                db.add(new_stroke)

        page.version += 1
        page.updated_at = datetime.utcnow()
        db.flush()
        db.refresh(page)
        return page


subject_repository = SubjectRepository()
lesson_repository = LessonRepository()
page_repository = PageRepository()
