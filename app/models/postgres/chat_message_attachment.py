from datetime import datetime

from sqlalchemy import Integer, String, ForeignKey, DateTime, func, Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase


class ChatMessageAttachment(PostgresBase):
    __tablename__ = "chat_message_attachments"
    __table_args__ = (
        Index("ix_chat_message_attachments_chat_id", "chat_id"),
        Index("ix_chat_message_attachments_message_id", "message_id"),
        Index("ix_chat_message_attachments_uploader_id", "uploader_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    chat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=True
    )
    uploader_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    type: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="attachments")

    def __repr__(self):
        return (
            f"<ChatMessageAttachment id={self.id} chat={self.chat_id} "
            f"message={self.message_id} uploader={self.uploader_id}>"
        )
