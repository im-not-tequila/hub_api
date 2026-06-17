from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres_connection import PostgresBase


class LegacyChatMessageMapping(PostgresBase):
    __tablename__ = "legacy_chat_message_mappings"
    __table_args__ = (
        UniqueConstraint("legacy_mailtoid", name="uq_legacy_chat_message_mappings_mailtoid"),
        UniqueConstraint("new_message_id", name="uq_legacy_chat_message_mappings_message_id"),
        Index("ix_legacy_chat_message_mappings_legacy_mailid", "legacy_mailid"),
        Index("ix_legacy_chat_message_mappings_chat_id", "chat_id"),
        Index("ix_legacy_chat_message_mappings_sender_user_id", "sender_user_id"),
        Index("ix_legacy_chat_message_mappings_recipient_user_id", "recipient_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    legacy_mailid: Mapped[int] = mapped_column(Integer, nullable=False)
    legacy_mailtoid: Mapped[int] = mapped_column(Integer, nullable=False)

    chat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    )
    new_message_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    migrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return (
            f"<LegacyChatMessageMapping legacy_mailid={self.legacy_mailid} "
            f"legacy_mailtoid={self.legacy_mailtoid} new_message={self.new_message_id}>"
        )
