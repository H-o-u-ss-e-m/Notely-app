from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from app.core.limits import MAX_STROKES_PER_REQUEST, MAX_CANVAS_DIM
from app.schemas.strokes import Stroke, check_total_points


class RecognitionOptions(BaseModel):
    debug: bool = False               # False = pas d'image base64
    deskew: bool = True
    language: str = "fr"              # fr | en | ar | de | auto
    num_beams: int = 1                # 1 = greedy (rapide) ; 2/4 = beam search
    include_thumbnails: bool = False  # Inclure miniature par ligne
    with_words: bool = True           # Extraire le détail des mots et confiances


class RecognitionRequest(BaseModel):
    strokes: List[Stroke] = Field(max_length=MAX_STROKES_PER_REQUEST)
    options: Optional[RecognitionOptions] = Field(default_factory=RecognitionOptions)
    canvasWidth: float = Field(default=1200.0, gt=0, le=MAX_CANVAS_DIM)
    canvasHeight: float = Field(default=800.0, gt=0, le=MAX_CANVAS_DIM)

    @model_validator(mode="after")
    def _limit_total_points(self):
        check_total_points(self.strokes)
        return self


class LineSegmentationResult(BaseModel):
    id: int
    stroke_ids: List[str]
    bbox: List[float]  # [xMin, yMin, xMax, yMax]
    center_y: float
    slanted_angle: float


class WordResult(BaseModel):
    index: int
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    calibrated: bool = False  # False = confiance heuristique indicative (§8.4)
    alternatives: List[str] = Field(default_factory=list)
    bbox: Optional[List[float]] = None
    corrected: bool = False
    original: Optional[str] = None
    source: Optional[str] = None  # "model" | "memory" | "dictionary"


class LineRecognitionResult(BaseModel):
    id: int
    stroke_ids: List[str]
    bbox: List[float]  # [xMin, yMin, xMax, yMax]
    text: str
    confidence: float
    calibrated: bool = False  # False = confiance heuristique (§8.4)
    min_word_confidence: float = 0.0
    words: List[WordResult] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    thumbnail: Optional[str] = None  # Miniature WebP ≤ 8 Ko si include_thumbnails
    image_base64: Optional[str] = None  # Rétrocompatibilité
    engine: str = "trocr"
    model_version: str = "v3"
    source: Optional[str] = None  # "model" | "memory" | "dictionary"
    stroke_fingerprint: Optional[str] = None


class RecognitionResponse(BaseModel):
    success: bool = True
    processingTimeMs: float
    lineCount: int
    lines: List[LineRecognitionResult]
    fullText: str
    modelName: str
    modelVersion: str = "v3"
    model_version: str = "v3"
    language: str = "fr"
    calibrated: bool = False  # False = confiance indicative


class SegmentationResponse(BaseModel):
    lines: List[LineSegmentationResult]
    medianStrokeHeight: float
    strokeCount: int


class ReOCRLineRequest(BaseModel):
    stroke_ids: List[str] = Field(max_length=MAX_STROKES_PER_REQUEST)
    strokes: List[Stroke] = Field(max_length=MAX_STROKES_PER_REQUEST)
    canvasWidth: float = Field(default=1200.0, gt=0, le=MAX_CANVAS_DIM)
    canvasHeight: float = Field(default=800.0, gt=0, le=MAX_CANVAS_DIM)

    @model_validator(mode="after")
    def _limit_total_points(self):
        check_total_points(self.strokes)
        return self


class LineWordsRequest(BaseModel):
    stroke_ids: List[str] = Field(max_length=MAX_STROKES_PER_REQUEST)
    strokes: List[Stroke] = Field(max_length=MAX_STROKES_PER_REQUEST)
    language: str = "fr"
    num_beams: int = 1
    include_thumbnail: bool = True
    canvasWidth: float = Field(default=1200.0, gt=0, le=MAX_CANVAS_DIM)
    canvasHeight: float = Field(default=800.0, gt=0, le=MAX_CANVAS_DIM)

    @model_validator(mode="after")
    def _limit_total_points(self):
        check_total_points(self.strokes)
        return self
