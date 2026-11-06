"""
Interface de base des moteurs OCR (ML-1 / §8.1).
Définit WordOut, LineOut et le protocole OcrEngine.
"""
from dataclasses import dataclass, field
from typing import Protocol, Sequence, Optional, List
from PIL import Image


@dataclass
class WordOut:
    index: int
    text: str
    confidence: float                       # confiance calibrée [0, 1]
    alternatives: List[str] = field(default_factory=list)
    bbox: Optional[List[float]] = None      # [xMin, yMin, xMax, yMax] repère page
    corrected: bool = False                 # modifié par dictionnaire ou utilisateur
    original: Optional[str] = None


@dataclass
class LineOut:
    text: str
    confidence: float                       # confiance combinée (pondérée + min)
    min_word_confidence: float
    words: List[WordOut] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)   # n-best de la ligne
    engine: str = ""
    model_version: str = ""
    thumbnail: Optional[str] = None         # Base64 WebP / PNG si demandé


class OcrEngine(Protocol):
    name: str
    version: str
    languages: frozenset[str]

    def recognize_lines(
        self,
        images: Sequence[Image.Image],
        *,
        num_beams: int = 1,
        n_best: int = 3,
        with_words: bool = True,
    ) -> List[LineOut]:
        ...

    def unload(self) -> None:
        ...
