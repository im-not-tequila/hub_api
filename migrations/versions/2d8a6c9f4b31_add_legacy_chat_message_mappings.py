"""add legacy chat message mappings

Revision ID: 2d8a6c9f4b31
Revises: 5e19a4981b58
Create Date: 2026-06-16 13:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2d8a6c9f4b31"
down_revision: Union[str, Sequence[str], None] = "5e19a4981b58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "legacy_chat_message_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("legacy_mailid", sa.Integer(), nullable=False),
        sa.Column("legacy_mailtoid", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("new_message_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("migrated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["new_message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_mailtoid", name="uq_legacy_chat_message_mappings_mailtoid"),
        sa.UniqueConstraint("new_message_id", name="uq_legacy_chat_message_mappings_message_id"),
    )
    op.create_index(
        "ix_legacy_chat_message_mappings_chat_id",
        "legacy_chat_message_mappings",
        ["chat_id"],
        unique=False,
    )
    op.create_index(
        "ix_legacy_chat_message_mappings_legacy_mailid",
        "legacy_chat_message_mappings",
        ["legacy_mailid"],
        unique=False,
    )
    op.create_index(
        "ix_legacy_chat_message_mappings_recipient_user_id",
        "legacy_chat_message_mappings",
        ["recipient_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_legacy_chat_message_mappings_sender_user_id",
        "legacy_chat_message_mappings",
        ["sender_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_legacy_chat_message_mappings_sender_user_id", table_name="legacy_chat_message_mappings")
    op.drop_index("ix_legacy_chat_message_mappings_recipient_user_id", table_name="legacy_chat_message_mappings")
    op.drop_index("ix_legacy_chat_message_mappings_legacy_mailid", table_name="legacy_chat_message_mappings")
    op.drop_index("ix_legacy_chat_message_mappings_chat_id", table_name="legacy_chat_message_mappings")
    op.drop_table("legacy_chat_message_mappings")
