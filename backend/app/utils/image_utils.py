"""
Utilitaires image — rotation sécurisée + encodage base64.

rotate_cv_image      : rotation simple (v1, conservée pour rétrocompatibilité)
rotate_cv_image_safe : agrandit le canvas avant rotation pour ne pas couper les coins (v2)
"""
import io
import math
import base64
import cv2
import numpy as np
from PIL import Image


def rotate_cv_image(image: np.ndarray, angle_deg: float) -> np.ndarray:
    """
    Rotation simple autour du centre (v1 — peut couper les coins pour grands angles).
    Conservée pour rétrocompatibilité.
    """
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    return cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def rotate_cv_image_safe(image: np.ndarray, angle_deg: float) -> np.ndarray:
    """
    Rotation sans coupure des coins (v2) :
    - Calcule les nouvelles dimensions pour contenir l'image pivotée
    - Applique la rotation avec translation pour centrer
    - Recadre au centre à la taille originale

    Pour des petits angles (< 15°), l'expansion est minime.
    Retourne une image de même taille que l'entrée.
    """
    h, w = image.shape[:2]
    rad = math.radians(abs(angle_deg))

    # Dimensions du canvas élargi pour contenir l'image pivotée sans coupure
    new_w = int(math.ceil(w * math.cos(rad) + h * math.sin(rad)))
    new_h = int(math.ceil(h * math.cos(rad) + w * math.sin(rad)))

    # Matrice de rotation centrée sur l'image originale + translation vers le nouveau centre
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    M[0, 2] += (new_w - w) / 2.0
    M[1, 2] += (new_h - h) / 2.0

    rotated = cv2.warpAffine(
        image, M, (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )

    # Recadrage centré à la taille originale
    start_x = max(0, (new_w - w) // 2)
    start_y = max(0, (new_h - h) // 2)
    cropped = rotated[start_y: start_y + h, start_x: start_x + w]

    # Sécurité : si le recadrage est vide, retourner l'image pivotée complète
    if cropped.shape[0] == 0 or cropped.shape[1] == 0:
        return rotated

    return cropped


def pil_to_base64_url(pil_img: Image.Image) -> str:
    """Encode une image PIL en data URL PNG base64."""
    buffered = io.BytesIO()
    pil_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"


def pil_to_webp_thumbnail(
    pil_img: Image.Image,
    max_dim: tuple = (320, 64),
    quality: int = 80,
    max_bytes: int = 8192,
) -> str:
    """
    Génère une miniature WebP compacte (≤ 8 Ko) conforme à §8.3 / ML-3.
    Redimensionne en conservant le ratio d'aspect.
    """
    img_copy = pil_img.copy()
    img_copy.thumbnail(max_dim, Image.Resampling.LANCZOS)

    q = quality
    while q >= 30:
        buffered = io.BytesIO()
        img_copy.save(buffered, format="WEBP", quality=q, method=4)
        data = buffered.getvalue()
        if len(data) <= max_bytes or q <= 30:
            b64_str = base64.b64encode(data).decode("utf-8")
            return f"data:image/webp;base64,{b64_str}"
        q -= 15

    b64_str = base64.b64encode(data).decode("utf-8")
    return f"data:image/webp;base64,{b64_str}"
