"""Configuration de test : variables d'environnement posees AVANT tout import de l'app."""
import os

os.environ["JWT_SECRET_KEY"] = "pytest-only-secret-0123456789-abcdefghijklmnop-QRSTUV"
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/notely_test")
os.environ["ENV"] = "dev"
os.environ["CORS_ORIGINS"] = "http://localhost:4200"
