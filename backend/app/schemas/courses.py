"""
Schémas DTO et Entités pour le domaine Cours / Espaces / Notes.
Respecte les normes de séparation DTO (Data Transfer Object) et Entités.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from app.core.limits import (
    MAX_ID_LEN, MAX_POINTS_PER_STROKE, MAX_STROKES_PER_REQUEST, MAX_TOTAL_POINTS,
    MAX_CANVAS_DIM, MAX_PAGES_PER_LESSON,
)

# ==============================================================================
# DTOs et Entités pour les Tracés & Pages d'un Cours
# ==============================================================================

class PointDTO(BaseModel):
    x: float = Field(ge=-10_000, le=10_000)
    y: float = Field(ge=-10_000, le=10_000)
    timestamp: Optional[float] = None
    pressure: Optional[float] = 1.0

class BoundingBoxDTO(BaseModel):
    xMin: float
    yMin: float
    xMax: float
    yMax: float

class StrokeDTO(BaseModel):
    id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    points: List[PointDTO] = Field(max_length=MAX_POINTS_PER_STROKE)
    startTime: float
    endTime: float
    color: Optional[str] = "#000000"
    width: Optional[float] = 3.0
    tool: Optional[str] = "pen"  # 'pen', 'diagram', 'eraser'
    contentType: Optional[str] = "normal"  # 'normal', 'h1'..'h6'
    pointerType: Optional[str] = "touch"
    bbox: Optional[BoundingBoxDTO] = None

class NotebookPageDTO(BaseModel):
    id: str = Field(max_length=MAX_ID_LEN)
    pageNumber: int = 1
    strokes: List[StrokeDTO] = Field(default=[], max_length=MAX_STROKES_PER_REQUEST)
    redoStack: List[StrokeDTO] = Field(default=[], max_length=MAX_STROKES_PER_REQUEST)
    width: Optional[float] = Field(default=794.0, gt=0, le=MAX_CANVAS_DIM)
    height: Optional[float] = Field(default=1123.0, gt=0, le=MAX_CANVAS_DIM)

    @model_validator(mode="after")
    def _limit_total_points(self):
        if sum(len(s.points) for s in self.strokes) > MAX_TOTAL_POINTS:
            raise ValueError(f"Trop de points sur la page (max {MAX_TOTAL_POINTS})")
        return self

# ==============================================================================
# Entités et DTOs pour les Cours (Lessons) et Espaces (Subjects)
# ==============================================================================

class LessonCreateDTO(BaseModel):
    title: str = Field(..., min_length=1, description="Titre du cours ou de la leçon")
    subjectId: str = Field(..., description="Identifiant de l'espace de rattachement")
    pages: Optional[List[NotebookPageDTO]] = Field(default=None, max_length=MAX_PAGES_PER_LESSON)

class LessonUpdateDTO(BaseModel):
    title: Optional[str] = None
    pages: Optional[List[NotebookPageDTO]] = Field(default=None, max_length=MAX_PAGES_PER_LESSON)
    pageCount: Optional[int] = None
    version: Optional[int] = None

class LessonEntity(BaseModel):
    id: str
    subjectId: str
    title: str
    updatedAt: str
    pageCount: int = 1
    pages: List[NotebookPageDTO] = []
    version: int = 1

class SubjectCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, description="Nom de l'espace ou matière")
    color: Optional[str] = Field(default="#1E40AF", description="Code couleur Hex")
    description: Optional[str] = ""

class SubjectUpdateDTO(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None

class SubjectEntity(BaseModel):
    id: str
    name: str
    color: str
    description: Optional[str] = ""
    lessons: List[LessonEntity] = []
    createdAt: Optional[str] = None
