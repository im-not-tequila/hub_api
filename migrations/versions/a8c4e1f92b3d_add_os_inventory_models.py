"""add os inventory models

Revision ID: a8c4e1f92b3d
Revises: f3a1d8e2b7c9
Create Date: 2026-06-26 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8c4e1f92b3d"
down_revision: Union[str, Sequence[str], None] = "f3a1d8e2b7c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "os_import_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_os_import_snapshots_imported_at", "os_import_snapshots", ["imported_at"], unique=False)
    op.create_index("ix_os_import_snapshots_is_current", "os_import_snapshots", ["is_current"], unique=False)

    op.create_table(
        "os_responsible_persons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=32), nullable=False, comment="ID МОЛ в 1С (поле ID из выгрузки)"),
        sa.Column("iin", sa.String(length=12), nullable=True),
        sa.Column("full_name", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_os_responsible_persons_external_id", "os_responsible_persons", ["external_id"], unique=False)
    op.create_index("ix_os_responsible_persons_iin", "os_responsible_persons", ["iin"], unique=False)

    op.create_table(
        "os_fixed_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "inventory_number",
            sa.String(length=32),
            nullable=False,
            comment="Инвентарный номер (par.inv)",
        ),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("acquisition_date", sa.Date(), nullable=True),
        sa.Column("price", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inventory_number"),
    )
    op.create_index("ix_os_fixed_assets_inventory_number", "os_fixed_assets", ["inventory_number"], unique=True)

    op.create_table(
        "os_snapshot_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["os_fixed_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["os_responsible_persons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["os_import_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "person_id",
            "asset_id",
            name="uq_os_snapshot_holdings_snapshot_person_asset",
        ),
    )
    op.create_index("ix_os_snapshot_holdings_asset_id", "os_snapshot_holdings", ["asset_id"], unique=False)
    op.create_index("ix_os_snapshot_holdings_person_id", "os_snapshot_holdings", ["person_id"], unique=False)
    op.create_index("ix_os_snapshot_holdings_snapshot_id", "os_snapshot_holdings", ["snapshot_id"], unique=False)
    op.create_index(
        "ix_os_snapshot_holdings_snapshot_asset",
        "os_snapshot_holdings",
        ["snapshot_id", "asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_os_snapshot_holdings_snapshot_person",
        "os_snapshot_holdings",
        ["snapshot_id", "person_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_os_snapshot_holdings_snapshot_person", table_name="os_snapshot_holdings")
    op.drop_index("ix_os_snapshot_holdings_snapshot_asset", table_name="os_snapshot_holdings")
    op.drop_index("ix_os_snapshot_holdings_snapshot_id", table_name="os_snapshot_holdings")
    op.drop_index("ix_os_snapshot_holdings_person_id", table_name="os_snapshot_holdings")
    op.drop_index("ix_os_snapshot_holdings_asset_id", table_name="os_snapshot_holdings")
    op.drop_table("os_snapshot_holdings")

    op.drop_index("ix_os_fixed_assets_inventory_number", table_name="os_fixed_assets")
    op.drop_table("os_fixed_assets")

    op.drop_index("ix_os_responsible_persons_iin", table_name="os_responsible_persons")
    op.drop_index("ix_os_responsible_persons_external_id", table_name="os_responsible_persons")
    op.drop_table("os_responsible_persons")

    op.drop_index("ix_os_import_snapshots_is_current", table_name="os_import_snapshots")
    op.drop_index("ix_os_import_snapshots_imported_at", table_name="os_import_snapshots")
    op.drop_table("os_import_snapshots")
