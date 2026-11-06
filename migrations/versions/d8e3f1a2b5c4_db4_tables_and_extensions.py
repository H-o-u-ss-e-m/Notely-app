"""Tables DB-4 et extensions (user_settings, user_dictionaries, ocr_jobs, model_versions, audit_logs, ocr_corrections)

Revision ID: d8e3f1a2b5c4
Revises: c7e2d9a4b1f8
Create Date: 2026-11-05

Tables et extensions pour P4 (DB-4 / ML-5 / SEC-8 / ARCH-2).
Migration expand-only réversible sans DROP destructif.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d8e3f1a2b5c4"
down_revision: Union[str, Sequence[str], None] = "c7e2d9a4b1f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. user_settings
    op.create_table(
        "user_settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("consent_train", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("consent_cloud_ocr", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("consent_withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ocr_language", sa.String(10), server_default="fr", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. user_dictionaries
    op.create_table(
        "user_dictionaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(10), server_default="fr", nullable=False),
        sa.Column("wrong", sa.String(100), nullable=False),
        sa.Column("right", sa.String(100), nullable=False),
        sa.Column("count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "language", "wrong", name="uq_userdict"),
    )
    op.create_index("ix_user_dictionaries_user_id", "user_dictionaries", ["user_id"])

    # 3. ocr_jobs
    op.create_table(
        "ocr_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("progress", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ocr_jobs_user_id", "ocr_jobs", ["user_id"])

    # 4. model_versions
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(20), server_default="candidate", nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 5. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])

    # 6. Extensions ocr_corrections
    op.add_column("ocr_corrections", sa.Column("scope", sa.String(20), server_default="line", nullable=False))
    op.add_column("ocr_corrections", sa.Column("word_index", sa.Integer(), nullable=True))
    op.add_column("ocr_corrections", sa.Column("stroke_fingerprint", sa.String(64), nullable=True))
    op.add_column("ocr_corrections", sa.Column("line_predicted", sa.Text(), nullable=True))
    op.add_column("ocr_corrections", sa.Column("line_corrected", sa.Text(), nullable=True))
    op.add_column("ocr_corrections", sa.Column("alternatives", postgresql.JSONB(), nullable=True))
    op.add_column("ocr_corrections", sa.Column("source", sa.String(20), server_default="manual", nullable=False))
    op.add_column("ocr_corrections", sa.Column("consent_withdrawn_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_ocr_corrections_fingerprint", "ocr_corrections", ["stroke_fingerprint"])


def downgrade() -> None:
    # Reverse ocr_corrections
    op.drop_index("ix_ocr_corrections_fingerprint", table_name="ocr_corrections")
    op.drop_column("ocr_corrections", "consent_withdrawn_at")
    op.drop_column("ocr_corrections", "source")
    op.drop_column("ocr_corrections", "alternatives")
    op.drop_column("ocr_corrections", "line_corrected")
    op.drop_column("ocr_corrections", "line_predicted")
    op.drop_column("ocr_corrections", "stroke_fingerprint")
    op.drop_column("ocr_corrections", "word_index")
    op.drop_column("ocr_corrections", "scope")

    # Reverse audit_logs
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    # Reverse model_versions
    op.drop_table("model_versions")

    # Reverse ocr_jobs
    op.drop_index("ix_ocr_jobs_user_id", table_name="ocr_jobs")
    op.drop_table("ocr_jobs")

    # Reverse user_dictionaries
    op.drop_index("ix_user_dictionaries_user_id", table_name="user_dictionaries")
    op.drop_table("user_dictionaries")

    # Reverse user_settings
    op.drop_table("user_settings")
