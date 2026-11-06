"""Ajout de ink_hash (hash visuel tolérant 256 bits) dans ocr_corrections

Revision ID: e9f1a2b3c4d5
Revises: d8e3f1a2b5c4
Create Date: 2026-11-06

Mission 1 (Partie 1.4 — Plan d'amélioration v2) :
Ajout de la colonne ink_hash et de son index pour la recherche tolérante par distance de Hamming.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e9f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "d8e3f1a2b5c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ocr_corrections", sa.Column("ink_hash", sa.String(64), nullable=True))
    op.create_index("ix_ocr_corrections_ink_hash", "ocr_corrections", ["ink_hash"])


def downgrade() -> None:
    op.drop_index("ix_ocr_corrections_ink_hash", table_name="ocr_corrections")
    op.drop_column("ocr_corrections", "ink_hash")
