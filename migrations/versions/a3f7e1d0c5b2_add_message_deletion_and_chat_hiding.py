"""add message deletion and chat hiding

Revision ID: a3f7e1d0c5b2
Revises: 2d8a6c9f4b31
Create Date: 2026-06-17 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3f7e1d0c5b2"
down_revision: Union[str, Sequence[str], None] = "2d8a6c9f4b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- chat_messages: поля soft-delete для всех ---
    op.add_column(
        "chat_messages",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "chat_messages",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("deleted_by_user_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_chat_messages_is_deleted", "chat_messages", ["is_deleted"])
    op.create_foreign_key(
        "fk_chat_messages_deleted_by_user_id",
        "chat_messages",
        "users",
        ["deleted_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- chat_message_user_deletions: скрытие сообщения у себя ---
    op.create_table(
        "chat_message_user_deletions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("message_id", "user_id", name="uq_chat_message_user_deletions_message_user"),
    )
    op.create_index(
        "ix_chat_message_user_deletions_message_id",
        "chat_message_user_deletions",
        ["message_id"],
    )
    op.create_index(
        "ix_chat_message_user_deletions_user_id",
        "chat_message_user_deletions",
        ["user_id"],
    )

    # --- chat_participants: скрытие чата у себя ---
    op.add_column(
        "chat_participants",
        sa.Column("chat_hidden_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_participants", "chat_hidden_at")

    op.drop_index("ix_chat_message_user_deletions_user_id", table_name="chat_message_user_deletions")
    op.drop_index("ix_chat_message_user_deletions_message_id", table_name="chat_message_user_deletions")
    op.drop_table("chat_message_user_deletions")

    op.drop_constraint("fk_chat_messages_deleted_by_user_id", "chat_messages", type_="foreignkey")
    op.drop_index("ix_chat_messages_is_deleted", table_name="chat_messages")
    op.drop_column("chat_messages", "deleted_by_user_id")
    op.drop_column("chat_messages", "deleted_at")
    op.drop_column("chat_messages", "is_deleted")
