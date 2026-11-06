"""Alembic env.py : l'URL de base provient de DATABASE_URL (jamais d'URL en dur dans alembic.ini)."""
import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_ROOT, "backend"))
load_dotenv(os.path.join(_ROOT, ".env"))

from app.db.base import Base  # noqa: E402
import app.db.models  # noqa: E402,F401  (enregistre TOUS les modeles dans Base.metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_url = os.getenv("DATABASE_URL", "").strip()
if not _url:
    raise RuntimeError("DATABASE_URL manquante : definissez-la dans .env ou l'environnement.")
config.set_main_option("sqlalchemy.url", _url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
