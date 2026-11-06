from PIL import Image
from typing import Tuple
from app.ml.trocr_engine import trocr_engine

class OCRService:
    @staticmethod
    def recognize_crop(pil_crop: Image.Image) -> Tuple[str, float]:
        return trocr_engine.recognize_line(pil_crop)

ocr_service = OCRService()
