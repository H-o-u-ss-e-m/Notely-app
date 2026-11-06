"""ocr_corrections (idempotent) + index de requetes

Revision ID: a1c3f0d2b7e4
Revises: e7dfa0ab488e
Create Date: 2026-11-05

La table ocr_corrections existait deja sur les bases creees via create_all() (avant Alembic) :
la creation est donc conditionnelle. Operation 100 % additive, aucune donnee modifiee.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1c3f0d2b7e4"
down_revision: Union[str, Sequence[str], None] = "e7dfa0ab488e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("ocr_corrections"):
        op.create_table(
            "ocr_corrections",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("page_id", sa.UUID(), nullable=True),
            sa.Column("stroke_ids", postgresql.ARRAY(sa.Text()), nullable=False),
            sa.Column("strokes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("engine", sa.String(length=100), nullable=False),
            sa.Column("model_version", sa.String(length=50), nullable=True),
            sa.Column("language", sa.String(length=10), nullable=False),
            sa.Column("predicted_text", sa.Text(), nullable=False),
            sa.Column("corrected_text", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("consent_train", sa.Boolean(), nullable=False),
            sa.Column("is_validated", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["page_id"], ["notebook_pages.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ocr_corrections_page_id"), "ocr_corrections", ["page_id"])
        op.create_index(op.f("ix_ocr_corrections_user_id"), "ocr_corrections", ["user_id"])


def downgrade() -> None:
    # Volontairement non destructif : on ne supprime pas ocr_corrections (donnees utilisateur).
    pass
