"""
Contrôleur REST API pour les Espaces (Subjects) et Cours (Lessons).
Support de l'authentification et isolation stricte par utilisateur.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Response, Header, status
from app.schemas.courses import (
    SubjectEntity, SubjectCreateDTO, SubjectUpdateDTO,
    LessonEntity, LessonCreateDTO, LessonUpdateDTO
)
from app.schemas.structural import PDFRawExportRequest, StructuralHTRRequest
from app.services.course_service import course_service
from app.services.pdf_raw_generator import pdf_raw_generator_service
from app.services.pdf_generator_service import pdf_generator_service
from app.services.structural_htr_service import structural_htr_service
from app.core.security import extract_user_id_from_header

router = APIRouter()

# ==============================================================================
# Endpoints Espaces / Matières (Subjects)
# ==============================================================================

@router.get("/courses/subjects", response_model=List[SubjectEntity], summary="Lister tous les espaces")
async def get_all_subjects(authorization: Optional[str] = Header(None)):
    """
    Récupère l'arborescence des Espaces et Cours enregistrés pour l'utilisateur connecté.
    """
    user_id = extract_user_id_from_header(authorization)
    return course_service.list_subjects(user_id)

@router.get("/courses/subjects/{subject_id}", response_model=SubjectEntity, summary="Détail d'un espace")
async def get_subject(subject_id: str, authorization: Optional[str] = Header(None)):
    user_id = extract_user_id_from_header(authorization)
    subject = course_service.get_subject_by_id(subject_id, user_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Espace introuvable")
    return subject

@router.post("/courses/subjects", response_model=SubjectEntity, status_code=status.HTTP_201_CREATED, summary="Créer un espace")
async def create_subject(dto: SubjectCreateDTO, authorization: Optional[str] = Header(None)):
    """
    Crée un nouvel espace de travail / matière pour l'utilisateur.
    """
    user_id = extract_user_id_from_header(authorization)
    if not dto.name.strip():
        raise HTTPException(status_code=400, detail="Le nom de l'espace est obligatoire")
    return course_service.create_subject(dto, user_id)

@router.put("/courses/subjects/{subject_id}", response_model=SubjectEntity, summary="Modifier un espace")
async def update_subject(subject_id: str, dto: SubjectUpdateDTO, authorization: Optional[str] = Header(None)):
    user_id = extract_user_id_from_header(authorization)
    subject = course_service.update_subject(subject_id, dto, user_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Espace introuvable")
    return subject

@router.delete("/courses/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un espace")
async def delete_subject(subject_id: str, authorization: Optional[str] = Header(None)):
    user_id = extract_user_id_from_header(authorization)
    success = course_service.delete_subject(subject_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Espace introuvable")
    return None

# ==============================================================================
# Endpoints Cours / Leçons (Lessons)
# ==============================================================================

@router.post("/courses/lessons", response_model=LessonEntity, status_code=status.HTTP_201_CREATED, summary="Créer un cours")
async def create_lesson(dto: LessonCreateDTO, authorization: Optional[str] = Header(None)):
    """
    Crée un nouveau cours rattaché à un espace de l'utilisateur.
    """
    user_id = extract_user_id_from_header(authorization)
    lesson = course_service.create_lesson(dto, user_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Espace de rattachement introuvable")
    return lesson

@router.get("/courses/subjects/{subject_id}/lessons/{lesson_id}", response_model=LessonEntity, summary="Détail d'un cours")
async def get_lesson(subject_id: str, lesson_id: str, authorization: Optional[str] = Header(None)):
    user_id = extract_user_id_from_header(authorization)
    lesson = course_service.get_lesson(subject_id, lesson_id, user_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    return lesson

@router.put("/courses/subjects/{subject_id}/lessons/{lesson_id}", response_model=LessonEntity, summary="Mettre à jour un cours")
async def update_lesson(subject_id: str, lesson_id: str, dto: LessonUpdateDTO, authorization: Optional[str] = Header(None)):
    """
    Met à jour un cours (titre, version ou contenu des tracés/pages).
    """
    user_id = extract_user_id_from_header(authorization)
    lesson = course_service.update_lesson(subject_id, lesson_id, dto, user_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Cours ou espace introuvable")
    return lesson

@router.delete("/courses/subjects/{subject_id}/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un cours")
async def delete_lesson(subject_id: str, lesson_id: str, authorization: Optional[str] = Header(None)):
    user_id = extract_user_id_from_header(authorization)
    success = course_service.delete_lesson(subject_id, lesson_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cours ou espace introuvable")
    return None

# ==============================================================================
# Endpoints d'Exportation PDF d'un cours enregistré
# ==============================================================================

@router.post("/courses/subjects/{subject_id}/lessons/{lesson_id}/export/pdf-raw", summary="Exporter PDF Original du cours")
async def export_lesson_pdf_raw(subject_id: str, lesson_id: str, authorization: Optional[str] = Header(None)):
    user_id = extract_user_id_from_header(authorization)
    subject = course_service.get_subject_by_id(subject_id, user_id)
    lesson = course_service.get_lesson(subject_id, lesson_id, user_id)
    if not subject or not lesson:
        raise HTTPException(status_code=404, detail="Cours ou Espace introuvable")

    raw_req = PDFRawExportRequest(
        subject=subject.name,
        lessonTitle=lesson.title,
        pages=[p.dict() for p in lesson.pages] if lesson.pages else []
    )
    pdf_bytes = pdf_raw_generator_service.generate_raw_pdf_bytes(raw_req)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{subject.name}_{lesson.title}_Original.pdf"'
        }
    )

@router.post("/courses/subjects/{subject_id}/lessons/{lesson_id}/export/pdf-ai", summary="Exporter PDF IA / OCR Structuré du cours")
async def export_lesson_pdf_ai(subject_id: str, lesson_id: str, authorization: Optional[str] = Header(None)):
    user_id = extract_user_id_from_header(authorization)
    subject = course_service.get_subject_by_id(subject_id, user_id)
    lesson = course_service.get_lesson(subject_id, lesson_id, user_id)
    if not subject or not lesson:
        raise HTTPException(status_code=404, detail="Cours ou Espace introuvable")

    htr_req = StructuralHTRRequest(
        pages=[p.dict() for p in lesson.pages] if lesson.pages else [],
        subject=subject.name,
        lessonTitle=lesson.title
    )
    htr_res = structural_htr_service.process_structural_strokes(htr_req)
    pdf_bytes = pdf_generator_service.generate_pdf_bytes(htr_res)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{subject.name}_{lesson.title}_AI_Structured.pdf"'
        }
    )
