from fastapi import Depends, APIRouter, HTTPException
from app.api.deps import current_user_id
from app.schemas.recognition import (
    RecognitionRequest,
    RecognitionResponse,
    ReOCRLineRequest,
    LineWordsRequest,
    LineRecognitionResult,
)
from app.services.handwriting_service import handwriting_service

router = APIRouter(dependencies=[Depends(current_user_id)])


@router.post("/recognition", response_model=RecognitionResponse, deprecated=True)
@router.post("/recognize", response_model=RecognitionResponse, deprecated=True)
async def recognize_strokes(request: RecognitionRequest, user_id=Depends(current_user_id)):
    """
    [DÉPRÉCIÉ — Préférer POST /api/v1/ocr/jobs (ARCH-2) pour les pages volumineuses]
    Inférence HTR synchrone (v3) :
    Strokes → Segmentation → Rendu configurable → TrOCR batch → Mots & alternatives → JSON.
    """
    try:
        return handwriting_service.process_strokes(
            strokes=request.strokes,
            canvas_w=request.canvasWidth,
            canvas_h=request.canvasHeight,
            options=request.options,
            user_id=str(user_id),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ocr/line-words", response_model=LineRecognitionResult)
@router.post("/line-words", response_model=LineRecognitionResult)
async def recognize_line_words(request: LineWordsRequest, user_id=Depends(current_user_id)):
    """
    Ré-analyse fine d'une ligne sélectionnée avec découpage mot par mot,
    confiances calibrées, alternatives n-best et miniature WebP/PNG (ML-3 / §8.3).
    """
    try:
        return handwriting_service.process_line_words(request, user_id=str(user_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reocr-line", response_model=LineRecognitionResult)
@router.post("/reocr_line", response_model=LineRecognitionResult)
async def reocr_single_line(request: ReOCRLineRequest):
    """
    Ré-inférence OCR sur une ligne spécifique sélectionnée (rétrocompatibilité).
    """
    try:
        return handwriting_service.reocr_line(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
