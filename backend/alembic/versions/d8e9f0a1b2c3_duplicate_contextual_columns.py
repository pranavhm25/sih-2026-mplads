"""Duplicate-candidate contextual validation columns

Revision ID: d8e9f0a1b2c3
Revises: c4d5e6f7a8b9
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa


revision = "d8e9f0a1b2c3"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "related_project",
        sa.Column("vendor_match", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "related_project",
        sa.Column("contextual_confidence", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("related_project", "contextual_confidence")
    op.drop_column("related_project", "vendor_match")
