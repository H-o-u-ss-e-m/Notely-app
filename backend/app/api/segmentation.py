from fastapi import Depends
from app.api.deps import current_user_id
import numpy as np
from fastapi import APIRouter, HTTPException
from app.schemas.recognition import RecognitionRequest, SegmentationResponse, LineSegmentationResult
from app.services.segmentation_service import segmentation_service

router = APIRouter(dependencies=[Depends(current_user_id)])

@router.post("/segmentation", response_model=SegmentationResponse)
@router.post("/segment_only", response_model=SegmentationResponse)
async def segment_strokes_only(request: RecognitionRequest):
    """
    Mode Debug indépendant :
    Retourne la segmentation adaptative des lignes et les bounding boxes sans exécuter TrOCR.
    """
    if not request.strokes:
        return SegmentationResponse(lines=[], medianStrokeHeight=0.0, strokeCount=0)

    try:
        line_groups = segmentation_service.segment_strokes(request.strokes)
        seg_results = [
            LineSegmentationResult(
                id=group["id"],
                stroke_ids=group["stroke_ids"],
                bbox=group["bbox"],
                center_y=group["center_y"],
                slanted_angle=group["slanted_angle"]
            )
            for group in line_groups
        ]

        valid_strokes = [s for s in request.strokes if s.tool != "eraser" and len(s.points) >= 2]
        heights = [s.calculate_bbox().yMax - s.calculate_bbox().yMin for s in valid_strokes]
        med_h = float(np.median(heights)) if heights else 0.0

        return SegmentationResponse(
            lines=seg_results,
            medianStrokeHeight=round(med_h, 2),
            strokeCount=len(valid_strokes)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
