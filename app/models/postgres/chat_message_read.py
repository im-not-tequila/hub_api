from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase


class ChatMessageRead(PostgresBase):
    __tablename__ = "chat_message_reads"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_chat_message_reads_message_user"),
        Index("ix_chat_message_reads_chat_id", "chat_id"),
        Index("ix_chat_message_reads_message_id", "message_id"),
        Index("ix_chat_message_reads_user_id", "user_id"),
        Index("ix_chat_message_reads_read_at", "read_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="reads")

    def __repr__(self):
        return (
            f"<ChatMessageRead id={self.id} chat={self.chat_id} "
            f"message={self.message_id} user={self.user_id}>"
        )
