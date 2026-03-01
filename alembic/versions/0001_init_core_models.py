"""init core models

Revision ID: 0001_init_core_models
Revises:
Create Date: 2026-02-12 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_init_core_models"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_centers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("identifier", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_work_centers_identifier", "work_centers", ["identifier"], unique=True)

    op.create_table(
        "batches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("task_description", sa.String(length=500), nullable=False),
        sa.Column("work_center_id", sa.Integer(), sa.ForeignKey("work_centers.id"), nullable=False),
        sa.Column("shift", sa.String(length=50), nullable=False),
        sa.Column("team", sa.String(length=255), nullable=False),
        sa.Column("batch_number", sa.Integer(), nullable=False),
        sa.Column("batch_date", sa.Date(), nullable=False),
        sa.Column("nomenclature", sa.String(length=255), nullable=False),
        sa.Column("ekn_code", sa.String(length=100), nullable=False),
        sa.Column("shift_start", sa.DateTime(), nullable=False),
        sa.Column("shift_end", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("batch_number", "batch_date", name="uq_batch_number_date"),
    )
    op.create_index("ix_batches_batch_number", "batches", ["batch_number"])
    op.create_index("ix_batches_batch_date", "batches", ["batch_date"])
    op.create_index("idx_batch_closed", "batches", ["is_closed"])
    op.create_index("idx_batch_shift_times", "batches", ["shift_start", "shift_end"])

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("unique_code", sa.String(length=128), nullable=False),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("is_aggregated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("aggregated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_products_unique_code", "products", ["unique_code"], unique=True)
    op.create_index("ix_products_batch_id", "products", ["batch_id"])
    op.create_index("idx_product_batch_aggregated", "products", ["batch_id", "is_aggregated"])

    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("events", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("secret_key", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("timeout", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("webhook_subscriptions.id"), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_subscriptions")
    op.drop_index("idx_product_batch_aggregated", table_name="products")
    op.drop_index("ix_products_batch_id", table_name="products")
    op.drop_index("ix_products_unique_code", table_name="products")
    op.drop_table("products")
    op.drop_index("idx_batch_shift_times", table_name="batches")
    op.drop_index("idx_batch_closed", table_name="batches")
    op.drop_index("ix_batches_batch_date", table_name="batches")
    op.drop_index("ix_batches_batch_number", table_name="batches")
    op.drop_table("batches")
    op.drop_index("ix_work_centers_identifier", table_name="work_centers")
    op.drop_table("work_centers")



