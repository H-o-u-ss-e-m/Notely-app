"""SEC-3: add family_id, used_at, user_agent to refresh_tokens

Revision ID: f1a2b3c4d5e6
Revises: e9f1a2b3c4d5
Create Date: 2026-11-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e9f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )
    op.add_column("refresh_tokens", sa.Column("used_at", sa.DateTime(), nullable=True))
    op.add_column("refresh_tokens", sa.Column("user_agent", sa.String(length=255), nullable=True))
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "user_agent")
    op.drop_column("refresh_tokens", "used_at")
    op.drop_column("refresh_tokens", "family_id")
