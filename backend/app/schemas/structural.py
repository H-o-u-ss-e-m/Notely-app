# -*- coding: utf-8 -*-
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from app.core.limits import MAX_STROKES_PER_REQUEST, MAX_PAGES_PER_REQUEST, MAX_CANVAS_DIM
from app.schemas.strokes import Stroke, check_total_points
from app.schemas.recognition import WordResult


class StructuralElement(BaseModel):
    id: int
    type: str  # 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'paragraph', 'diagram'
    text: str = ""
    confidence: float = 1.0
    calibrated: bool = False
    min_word_confidence: float = 1.0
    words: List[WordResult] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    thumbnail: Optional[str] = None
    bbox: List[float]  # [xMin, yMin, xMax, yMax]
    image_base64: Optional[str] = None
    stroke_ids: List[str] = Field(default_factory=list)
    pageNumber: int = 1


class PageData(BaseModel):
    pageNumber: int = 1
    strokes: List[Stroke] = Field(default=[], max_length=MAX_STROKES_PER_REQUEST)
    width: float = Field(default=1200.0, gt=0, le=MAX_CANVAS_DIM)
    height: float = Field(default=800.0, gt=0, le=MAX_CANVAS_DIM)

    @model_validator(mode="after")
    def _limit_total_points(self):
        check_total_points(self.strokes)
        return self


class StructuralHTRRequest(BaseModel):
    strokes: Optional[List[Stroke]] = Field(default=None, max_length=MAX_STROKES_PER_REQUEST)
    pages: Optional[List[PageData]] = Field(default=None, max_length=MAX_PAGES_PER_REQUEST)
    canvasWidth: float = Field(default=1200.0, gt=0, le=MAX_CANVAS_DIM)
    canvasHeight: float = Field(default=800.0, gt=0, le=MAX_CANVAS_DIM)
    subject: Optional[str] = Field(default="Cours Manuscrit", max_length=255)
    lessonTitle: Optional[str] = Field(default="Chapitre 1", max_length=255)
    language: Optional[str] = Field(default="fr", max_length=10)

    @model_validator(mode="after")
    def _limit_total_points(self):
        if self.strokes:
            check_total_points(self.strokes)
        return self


class StructuralHTRResponse(BaseModel):
    success: bool = True
    processingTimeMs: float
    subject: str
    lessonTitle: str
    elements: List[StructuralElement]
    fullMarkdown: str
    calibrated: bool = False


class PDFExportRequest(BaseModel):
    subject: str = Field(default="Cours Manuscrit", max_length=255)
    lessonTitle: str = Field(default="Chapitre 1", max_length=255)
    elements: List[StructuralElement] = Field(default_factory=list)
    pages: Optional[List[PageData]] = Field(default=None)


class PDFRawExportRequest(BaseModel):
    subject: str = Field(default="Cours Manuscrit", max_length=255)
    lessonTitle: str = Field(default="Chapitre 1", max_length=255)
    strokes: Optional[List[Stroke]] = Field(default=None, max_length=MAX_STROKES_PER_REQUEST)
    pages: Optional[List[PageData]] = Field(default=None, max_length=MAX_PAGES_PER_REQUEST)
    canvasWidth: float = Field(default=1200.0, gt=0, le=MAX_CANVAS_DIM)
    canvasHeight: float = Field(default=800.0, gt=0, le=MAX_CANVAS_DIM)
    language: str = "fr"
    pdfUrl: Optional[str] = None
