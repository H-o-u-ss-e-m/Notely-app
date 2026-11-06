from typing import List, Optional
from pydantic import BaseModel
from app.schemas.strokes import Stroke
from app.schemas.recognition import LineRecognitionResult

class DocumentCreate(BaseModel):
    title: str = "Sans titre"
    strokes: List[Stroke]
    lines: Optional[List[LineRecognitionResult]] = []
    fullText: Optional[str] = ""

class DocumentResponse(BaseModel):
    id: str
    title: str
    createdAt: str
    updatedAt: str
    strokes: List[Stroke]
    lines: List[LineRecognitionResult]
    fullText: str

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
