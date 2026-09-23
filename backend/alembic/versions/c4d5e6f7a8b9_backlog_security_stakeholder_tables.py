"""Backlog: security/stakeholder tables + officer extensions

Revision ID: c4d5e6f7a8b9
Revises: b7c1d90aa2f4
Create Date: 2026-09-23
"""
from alembic import op
import sqlalchemy as sa


revision = "c4d5e6f7a8b9"
down_revision = "b7c1d90aa2f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- officer extensions (backlog #2 auth + #4 scope) -------------------
    op.add_column("officer", sa.Column("stakeholder_role", sa.String(40), nullable=True))
    op.add_column("officer", sa.Column("constituency", sa.String(255), nullable=True))
    op.add_column("officer", sa.Column("state", sa.String(255), nullable=True))
    op.add_column("officer", sa.Column("password_hash", sa.String(255), nullable=True))

    # --- tamper-evident audit chain (backlog #2) ---------------------------
    op.create_table(
        "audit_event",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("seq", sa.Integer(), nullable=False, unique=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=True),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("entry_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_seq", "audit_event", ["seq"])
    op.create_index("ix_audit_action", "audit_event", ["action"])

    # --- alert digest watermark (backlog #6) --------------------------------
    op.create_table(
        "alert_digest",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("last_seen_seq", sa.Integer(), nullable=False),
        sa.Column("last_generated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # --- optional payments layer (backlog #5) --------------------------------
    op.create_table(
        "payment_record",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36),
                  sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("dataset_id", sa.String(36),
                  sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("payment_ref", sa.String(100), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("unit", sa.String(10), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.Column("payee", sa.String(255), nullable=True),
        sa.Column("stage", sa.String(50), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_payment_project", "payment_record", ["project_id"])

    # --- optional asset layer (backlog #5) ------------------------------------
    op.create_table(
        "asset_record",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36),
                  sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("dataset_id", sa.String(36),
                  sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("asset_description", sa.Text(), nullable=True),
        sa.Column("geo_tagged_photo_ref", sa.String(500), nullable=True),
        sa.Column("verification_status", sa.String(40), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("asset_record")
    op.drop_index("ix_payment_project", table_name="payment_record")
    op.drop_table("payment_record")
    op.drop_table("alert_digest")
    op.drop_index("ix_audit_action", table_name="audit_event")
    op.drop_index("ix_audit_seq", table_name="audit_event")
    op.drop_table("audit_event")
    op.drop_column("officer", "password_hash")
    op.drop_column("officer", "state")
    op.drop_column("officer", "constituency")
    op.drop_column("officer", "stakeholder_role")
