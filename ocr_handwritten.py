# -*- coding: utf-8 -*-
"""
Smart Handwriting Notebook Monorepo Launcher
Lance le backend FastAPI 3-tier et l'API versionnée /api/v1.
"""
import sys
import os

# Chemin absolu garanti vers le dossier backend
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.chdir(backend_dir)

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print("=" * 75)
    print("  SMART HANDWRITING NOTEBOOK MONOREPO (FastAPI + Angular + Flutter)")
    print(f"  Serveur REST API : http://localhost:{settings.PORT}{settings.API_V1_STR}")
    print(f"  Interface Web    : http://localhost:{settings.PORT}")
    print("=" * 75)

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)