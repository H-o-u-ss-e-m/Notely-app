"""index de requetes sur ocr_corrections (additif)

Revision ID: b4d8e1c9a5f2
Revises: a1c3f0d2b7e4
Create Date: 2026-11-05

Index utiles a la boucle d'apprentissage (plan §5.2). CREATE INDEX IF NOT EXISTS : idempotent,
aucune donnee modifiee.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b4d8e1c9a5f2"
down_revision: Union[str, Sequence[str], None] = "a1c3f0d2b7e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_corrections_user_lang "
        "ON ocr_corrections (user_id, language, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_corrections_train "
        "ON ocr_corrections (language) WHERE consent_train AND is_validated"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_corrections_train")
    op.execute("DROP INDEX IF EXISTS ix_corrections_user_lang")
