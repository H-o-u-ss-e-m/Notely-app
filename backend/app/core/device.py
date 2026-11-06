import torch
from app.core.config import settings

def get_optimal_device() -> str:
    """
    Détecte automatiquement si GPU CUDA est disponible, sinon utilise le CPU.
    """
    setting = settings.DEVICE_SETTING.lower()
    if setting == "cuda":
        return "cuda" if torch.cuda.is_available() else "cpu"
    elif setting == "cpu":
        return "cpu"
    else:  # auto
        return "cuda" if torch.cuda.is_available() else "cpu"
