"""
CourseRepository — Accès PostgreSQL pour Subjects, Lessons, Pages et Strokes (DB-3).
Toutes les opérations vérifient l'appartenance à l'utilisateur authentifié.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.db.models.course import Subject, Lesson, NotebookPage, Stroke


class StrokeIdConflict(ValueError):
    """ID de trace deja present sur une autre page (collision ou tentative d'ecrasement)."""


def _stroke_client_key(s) -> str:
    cid = getattr(s, "client_id", None)
    if isinstance(cid, str) and cid:
        return cid
    return str(getattr(s, "id", ""))


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
        """Charge un cours en vérifiant l'appartenance à l'utilisateur et qu'il n'est pas en corbeille."""
        return (
            db.query(Lesson)
            .join(Subject)
            .filter(Lesson.id == lesson_id, Subject.user_id == user_id, Lesson.deleted_at.is_(None))
            .options(joinedload(Lesson.pages).joinedload(NotebookPage.strokes))
            .first()
        )

    def get_by_subject(self, db: Session, subject_id: str, user_id: str) -> List[Lesson]:
        subj = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user_id).first()
        if not subj:
            return []
        return (
            db.query(Lesson)
            .filter(Lesson.subject_id == subject_id, Lesson.deleted_at.is_(None))
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
        """Suppression logique (corbeille 30 jours — DB-3)."""
        lesson.deleted_at = datetime.now(timezone.utc)
        db.flush()


class PageRepository:

    def get(self, db: Session, page_id: str, user_id: str) -> Optional[NotebookPage]:
        """Charge une page en vérifiant la chaîne page→lesson→subject→user."""
        return (
            db.query(NotebookPage)
            .join(Lesson)
            .join(Subject)
            .filter(NotebookPage.id == page_id, Subject.user_id == user_id, Lesson.deleted_at.is_(None))
            .options(joinedload(NotebookPage.strokes))
            .first()
        )

    def save_strokes(self, db: Session, page: NotebookPage, strokes_data: List[dict]) -> NotebookPage:
        """
        Fusion atomique des tracés par client_id (Stroke Merge — DB-3).
        """
        existing_by_key = {_stroke_client_key(s): s for s in (page.strokes or [])}
        existing_ids = set(existing_by_key.keys())
        incoming_ids = {s["id"] for s in strokes_data if s.get("id")}

        # SÉCURITÉ (anti-IDOR) : vérifier qu'un ID étranger n'est pas en conflit
        foreign_ids = incoming_ids - existing_ids
        if foreign_ids:
            clash = db.query(Stroke.id).filter(
                Stroke.client_id.in_(foreign_ids), Stroke.page_id != page.id
            ).first()
            if clash:
                raise StrokeIdConflict("Identifiant de trace deja utilise par une autre page.")

        # Suppression logique ou retrait des tracés qui n'existent plus dans la mise à jour complète
        if strokes_data:
            for key, s in list(existing_by_key.items()):
                if key not in incoming_ids:
                    if hasattr(s, "deleted_at"):
                        s.deleted_at = datetime.now(timezone.utc)
                    else:
                        db.delete(s)

        for idx, sdata in enumerate(strokes_data):
            stroke_id = sdata.get("id") or f"strk-{uuid.uuid4()}"
            if stroke_id in existing_by_key:
                stroke = existing_by_key[stroke_id]
                stroke.points = sdata.get("points", stroke.points)
                stroke.color = sdata.get("color", stroke.color)
                stroke.width = sdata.get("width", stroke.width)
                stroke.tool = sdata.get("tool", stroke.tool)
                stroke.content_type = sdata.get("contentType", stroke.content_type)
                stroke.bbox = sdata.get("bbox", stroke.bbox)
                stroke.seq = idx
                stroke.deleted_at = None
            else:
                new_stroke = Stroke(
                    id=uuid.uuid4(),
                    page_id=page.id,
                    client_id=stroke_id,
                    seq=idx,
                    tool=sdata.get("tool", "pen"),
                    content_type=sdata.get("contentType", "normal"),
                    color=sdata.get("color", "#000000"),
                    width=float(sdata.get("width", 3.0)),
                    points=sdata.get("points", []),
                    bbox=sdata.get("bbox"),
                    start_time=float(sdata.get("startTime", 0.0)),
                    end_time=float(sdata.get("endTime", 0.0)),
                    deleted_at=None,
                )
                db.add(new_stroke)

        page.version += 1
        page.updated_at = datetime.utcnow()
        db.flush()
        db.refresh(page)
        return page

    def patch_strokes_delta(
        self,
        db: Session,
        page: NotebookPage,
        added: List[dict],
        removed_client_ids: List[str],
    ) -> NotebookPage:
        """
        Sauvegarde différentielle (DB-3 / §5.7) :
        - Ajoute de manière idempotente (page_id, client_id) les tracés `added`
        - Marque `deleted_at = now()` sur les tracés de `removed_client_ids`
        - Incrémente `page.version`
        """
        active_strokes = db.query(Stroke).filter(Stroke.page_id == page.id).all()
        by_client_id = {
            (s.client_id if getattr(s, "client_id", None) else str(s.id)): s
            for s in active_strokes
        }
        next_seq = max((getattr(s, "seq", 0) or 0 for s in active_strokes), default=-1) + 1

        for sdata in added:
            cid = sdata.get("id") or f"strk-{uuid.uuid4()}"
            if cid in by_client_id:
                existing = by_client_id[cid]
                if getattr(existing, "deleted_at", None) is not None:
                    existing.deleted_at = None
                continue
            new_stroke = Stroke(
                id=uuid.uuid4(),
                page_id=page.id,
                client_id=cid,
                seq=next_seq,
                tool=sdata.get("tool", "pen"),
                content_type=sdata.get("contentType", "normal"),
                color=sdata.get("color", "#000000"),
                width=float(sdata.get("width", 3.0)),
                points=sdata.get("points", []),
                bbox=sdata.get("bbox"),
                start_time=float(sdata.get("startTime", 0.0)),
                end_time=float(sdata.get("endTime", 0.0)),
                deleted_at=None,
            )
            next_seq += 1
            db.add(new_stroke)
            by_client_id[cid] = new_stroke

        if removed_client_ids:
            now_utc = datetime.now(timezone.utc)
            removed_set = set(removed_client_ids)
            for cid in removed_set:
                if cid in by_client_id:
                    by_client_id[cid].deleted_at = now_utc

        page.version = (page.version or 0) + 1
        page.updated_at = datetime.utcnow()
        db.flush()
        db.commit()
        return page

    def list_active_strokes(self, db: Session, page_id) -> List[Stroke]:
        """Retourne les tracés actifs (`deleted_at IS NULL`) triés par `seq` (chargement paresseux §5.7)."""
        rows = (
            db.query(Stroke)
            .filter(Stroke.page_id == page_id, Stroke.deleted_at.is_(None))
            .order_by(Stroke.seq.asc(), Stroke.start_time.asc())
            .all()
        )
        return [s for s in rows if getattr(s, "deleted_at", None) is None]


subject_repository = SubjectRepository()
lesson_repository = LessonRepository()
page_repository = PageRepository()
