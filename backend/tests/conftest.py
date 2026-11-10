"""Configuration de test : variables d'environnement posées AVANT tout import de l'app."""
import os

os.environ["JWT_SECRET_KEY"] = "pytest-only-secret-0123456789-abcdefghijklmnop-QRSTUV"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ["ENV"] = "test"
os.environ["SKIP_MODEL_LOAD"] = "1"
os.environ["CORS_ORIGINS"] = "http://localhost:4200"
