"""datasets provenance extensions + typed record tables

Revision ID: b7c1d90aa2f4
Revises: 67e490029aa1
Create Date: 2026-09-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7c1d90aa2f4"
down_revision = "67e490029aa1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Dataset provenance extensions (nullable-safe for existing rows) ---
    with op.batch_alter_table("datasets") as batch:
        batch.add_column(sa.Column("dataset_type", sa.String(length=40), nullable=False,
                                   server_default="WORK_LEVEL"))
        batch.add_column(sa.Column("source_url", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("retrieved_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("file_name", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("file_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("source_schema", sa.JSON(), nullable=True))

    # --- Typed record tables (Prompt 3) ------------------------------------
    op.create_table(
        "mp_allocation_record",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("serial_number", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(length=255), nullable=True),
        sa.Column("mp_name", sa.String(length=255), nullable=True),
        sa.Column("constituency", sa.String(length=255), nullable=True),
        sa.Column("elected_nominated", sa.String(length=50), nullable=True),
        sa.Column("allocated_amount", sa.Numeric(16, 2), nullable=True),
        sa.Column("amount_unit", sa.String(length=10), nullable=False,
                  server_default="RUPEE"),
        sa.Column("source_row_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mpa_state", "mp_allocation_record", ["state"])
    op.create_index("ix_mpa_name", "mp_allocation_record", ["mp_name"])

    op.create_table(
        "scheme_aggregate",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("house", sa.String(length=20), nullable=True),
        sa.Column("allocated_limit", sa.Numeric(18, 2), nullable=True),
        sa.Column("amount_consented_for_calamity", sa.Numeric(18, 2), nullable=True),
        sa.Column("works_recommended", sa.Integer(), nullable=True),
        sa.Column("works_sanctioned", sa.Integer(), nullable=True),
        sa.Column("works_completed", sa.Integer(), nullable=True),
        sa.Column("expenditure_completed_and_ongoing", sa.Numeric(18, 2), nullable=True),
        sa.Column("monetary_unit", sa.String(length=10), nullable=False,
                  server_default="RUPEE"),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "validation_issue",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("field", sa.String(length=100), nullable=True),
        sa.Column("rule", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("observed_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vissue_dataset", "validation_issue", ["dataset_id"])
    op.create_index("ix_vissue_severity", "validation_issue", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_vissue_severity", table_name="validation_issue")
    op.drop_index("ix_vissue_dataset", table_name="validation_issue")
    op.drop_table("validation_issue")
    op.drop_table("scheme_aggregate")
    op.drop_index("ix_mpa_name", table_name="mp_allocation_record")
    op.drop_index("ix_mpa_state", table_name="mp_allocation_record")
    op.drop_table("mp_allocation_record")
    with op.batch_alter_table("datasets") as batch:
        batch.drop_column("source_schema")
        batch.drop_column("file_hash")
        batch.drop_column("file_name")
        batch.drop_column("retrieved_at")
        batch.drop_column("source_url")
        batch.drop_column("dataset_type")
