"""Add NOT_SUBSTANTIATED lifecycle support: resolution_reason column.

Case-status strings are data, not schema, so the new CLOSED status needs no
DDL. The one schema change is a structured reason category recorded when a
case is closed as not substantiated (PRD R12 extension).

Revision ID: e1a2b3c4d5e6
Revises: d8e9f0a1b2c3
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e1a2b3c4d5e6"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "investigation_case",
        sa.Column("resolution_reason", sa.String(length=40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("investigation_case", "resolution_reason")
