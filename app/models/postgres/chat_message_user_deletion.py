from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres_connection import PostgresBase


class ChatMessageUserDeletion(PostgresBase):
    """Фиксирует факт того, что пользователь скрыл сообщение только для себя."""

    __tablename__ = "chat_message_user_deletions"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_chat_message_user_deletions_message_user"),
        Index("ix_chat_message_user_deletions_message_id", "message_id"),
        Index("ix_chat_message_user_deletions_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<ChatMessageUserDeletion message={self.message_id} user={self.user_id}>"
