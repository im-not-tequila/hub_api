from datetime import datetime

from sqlalchemy import Integer, Text, Boolean, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase


class ChatMessage(PostgresBase):
    __tablename__ = 'chat_messages'
    __table_args__ = (
        Index('ix_chat_messages_chat_id', 'chat_id'),
        Index('ix_chat_messages_sender_id', 'sender_id'),
        Index('ix_chat_messages_created_at', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    chat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('chats.id', ondelete='CASCADE'), nullable=False
    )
    sender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false', nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage id={self.id} chat={self.chat_id} sender={self.sender_id}>"
