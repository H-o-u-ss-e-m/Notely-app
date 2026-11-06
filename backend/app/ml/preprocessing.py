import cv2
import numpy as np
from PIL import Image

class Preprocessor:
    @staticmethod
    def normalize_line_image(pil_img: Image.Image) -> Image.Image:
        """
        Assure la conversion RGB et le nettoyage des marges si nécessaire.
        """
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        return pil_img

preprocessor = Preprocessor()
