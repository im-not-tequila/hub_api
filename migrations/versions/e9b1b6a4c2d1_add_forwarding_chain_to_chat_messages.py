"""add forwarding chain fields to chat messages

Revision ID: e9b1b6a4c2d1
Revises: 36e9fe2cb23b
Create Date: 2026-05-13 12:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e9b1b6a4c2d1"
down_revision: Union[str, Sequence[str], None] = "36e9fe2cb23b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "chat_messages",
        sa.Column("forwarded_from_message_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("original_message_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("original_sender_id", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_chat_messages_forwarded_from_message_id",
        "chat_messages",
        ["forwarded_from_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_original_message_id",
        "chat_messages",
        ["original_message_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_chat_messages_forwarded_from_message_id",
        "chat_messages",
        "chat_messages",
        ["forwarded_from_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_chat_messages_original_message_id",
        "chat_messages",
        "chat_messages",
        ["original_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_chat_messages_original_sender_id",
        "chat_messages",
        "users",
        ["original_sender_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_chat_messages_original_sender_id", "chat_messages", type_="foreignkey")
    op.drop_constraint("fk_chat_messages_original_message_id", "chat_messages", type_="foreignkey")
    op.drop_constraint("fk_chat_messages_forwarded_from_message_id", "chat_messages", type_="foreignkey")

    op.drop_index("ix_chat_messages_original_message_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_forwarded_from_message_id", table_name="chat_messages")

    op.drop_column("chat_messages", "original_sender_id")
    op.drop_column("chat_messages", "original_message_id")
    op.drop_column("chat_messages", "forwarded_from_message_id")
