"""add broadcast groups

Revision ID: f3a1d8e2b7c9
Revises: c1d2e3f4a5b6
Create Date: 2026-06-17 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a1d8e2b7c9"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broadcast_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_broadcast_groups_created_by_user_id",
        "broadcast_groups",
        ["created_by_user_id"],
    )

    op.create_table(
        "broadcast_group_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("broadcast_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "added_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_id", "user_id", name="uq_broadcast_group_members_group_user"
        ),
    )
    op.create_index(
        "ix_broadcast_group_members_group_id",
        "broadcast_group_members",
        ["group_id"],
    )
    op.create_index(
        "ix_broadcast_group_members_user_id",
        "broadcast_group_members",
        ["user_id"],
    )

    op.create_table(
        "broadcast_group_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("broadcast_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_id", "role_id", name="uq_broadcast_group_roles_group_role"
        ),
    )
    op.create_index(
        "ix_broadcast_group_roles_group_id",
        "broadcast_group_roles",
        ["group_id"],
    )
    op.create_index(
        "ix_broadcast_group_roles_role_id",
        "broadcast_group_roles",
        ["role_id"],
    )


def downgrade() -> None:
    op.drop_table("broadcast_group_roles")
    op.drop_table("broadcast_group_members")
    op.drop_table("broadcast_groups")
