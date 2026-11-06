from fastapi import Depends
from app.api.deps import current_user_id
# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Response
from app.schemas.structural import StructuralHTRRequest, StructuralHTRResponse, PDFExportRequest, PDFRawExportRequest
from app.services.structural_htr_service import structural_htr_service
from app.services.pdf_generator_service import pdf_generator_service
from app.services.pdf_raw_generator import pdf_raw_generator_service

router = APIRouter(dependencies=[Depends(current_user_id)])

@router.post("/structural-htr", response_model=StructuralHTRResponse)
@router.post("/structural_htr", response_model=StructuralHTRResponse)
async def process_structural_htr(request: StructuralHTRRequest, user_id: str = Depends(current_user_id)):
    """
    Analyse HTR Structurelle :
    Identifie les Grands Titres (H1), Sous-Titres (H2), Textes et Découpe les Schémas/Dessins Géométriques.
    """
    try:
        return structural_htr_service.process_structural_strokes(request, user_id=str(user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export-pdf")
@router.post("/export_pdf")
async def export_course_pdf(request: PDFExportRequest):
    """
    Génère et télécharge un document PDF structuré de haute qualité du cours manuscrit.
    """
    try:
        pdf_bytes = pdf_generator_service.generate_pdf_bytes(request)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{request.subject}_{request.lessonTitle}.pdf"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la generation PDF : {str(e)}")

@router.post("/export-pdf-raw")
@router.post("/export_pdf_raw")
async def export_raw_pdf(request: PDFRawExportRequest):
    """
    Génère et télécharge un document PDF brut (dessin exact du canvas sans HTR).
    """
    try:
        pdf_bytes = pdf_raw_generator_service.generate_raw_pdf_bytes(request)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{request.subject}_{request.lessonTitle}_raw.pdf"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la generation PDF raw : {str(e)}")