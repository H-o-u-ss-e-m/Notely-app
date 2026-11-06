"""Mise a jour des dimensions par defaut de notebook_pages (794x1123 A4)

Revision ID: c7e2d9a4b1f8
Revises: b4d8e1c9a5f2
Create Date: 2026-11-05

Harmonisation dimensions A4 Flutter (794x1123) selon le plan DB-2 (constat #8).
Modifie uniquement les valeurs par defaut de la colonne sans alterer les donnees existantes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7e2d9a4b1f8"
down_revision: Union[str, Sequence[str], None] = "b4d8e1c9a5f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('notebook_pages', 'width', server_default='794.0')
    op.alter_column('notebook_pages', 'height', server_default='1123.0')


def downgrade() -> None:
    op.alter_column('notebook_pages', 'width', server_default='800.0')
    op.alter_column('notebook_pages', 'height', server_default='1000.0')
