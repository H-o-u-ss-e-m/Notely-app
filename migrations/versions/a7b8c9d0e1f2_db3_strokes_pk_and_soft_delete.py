"""DB-3: strokes UUID primary key, client_id unique per page, seq, deleted_at, and lessons.deleted_at

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-11-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "strokes",
        sa.Column(
            "uid",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )
    op.add_column("strokes", sa.Column("client_id", sa.String(length=255), nullable=True))
    op.add_column("strokes", sa.Column("seq", sa.Integer(), server_default="0", nullable=False))
    op.add_column("strokes", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE strokes SET client_id = id")
    op.alter_column("strokes", "client_id", nullable=False)
    op.drop_constraint("strokes_pkey", "strokes", type_="primary")
    op.drop_column("strokes", "id")
    op.alter_column("strokes", "uid", new_column_name="id")
    op.create_primary_key("strokes_pkey", "strokes", ["id"])
    op.create_unique_constraint("uq_strokes_page_client", "strokes", ["page_id", "client_id"])
    op.add_column("lessons", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("lessons", "deleted_at")
    op.drop_constraint("uq_strokes_page_client", "strokes", type_="unique")
    op.drop_constraint("strokes_pkey", "strokes", type_="primary")
    op.alter_column("strokes", "id", new_column_name="uid")
    op.add_column("strokes", sa.Column("id", sa.String(length=255), nullable=True))
    op.execute("UPDATE strokes SET id = client_id")
    op.alter_column("strokes", "id", nullable=False)
    op.create_primary_key("strokes_pkey", "strokes", ["id"])
    op.drop_column("strokes", "deleted_at")
    op.drop_column("strokes", "seq")
    op.drop_column("strokes", "client_id")
    op.drop_column("strokes", "uid")
