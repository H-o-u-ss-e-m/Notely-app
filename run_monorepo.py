import sys
import os
import uvicorn

# Ajouter backend au path Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.config import settings

if __name__ == "__main__":
    print("=" * 75)
    print("  SMART HANDWRITING NOTEBOOK MONOREPO (FastAPI + Angular + Flutter)")
    print(f"  Serveur REST API  : http://localhost:{settings.PORT}{settings.API_V1_STR}")
    print(f"  Interface Web     : http://localhost:{settings.PORT}")
    print(f"  Écoute Réseau Wi-Fi : http://0.0.0.0:{settings.PORT}")
    print(f"  Matériel Cible    : {settings.DEVICE_SETTING.upper()}")
    print("=" * 75)

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
