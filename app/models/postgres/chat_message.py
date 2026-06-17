from datetime import datetime

from sqlalchemy import Integer, Text, Boolean, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase


class ChatMessage(PostgresBase):
    __tablename__ = 'chat_messages'
    __table_args__ = (
        Index('ix_chat_messages_chat_id', 'chat_id'),
        Index('ix_chat_messages_sender_id', 'sender_id'),
        Index('ix_chat_messages_forwarded_from_message_id', 'forwarded_from_message_id'),
        Index('ix_chat_messages_original_message_id', 'original_message_id'),
        Index('ix_chat_messages_created_at', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    chat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('chats.id', ondelete='CASCADE'), nullable=False
    )
    sender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false', nullable=False)
    forwarded_from_message_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('chat_messages.id', ondelete='SET NULL'), nullable=True
    )
    original_message_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('chat_messages.id', ondelete='SET NULL'), nullable=True
    )
    original_sender_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
    attachments: Mapped[list["ChatMessageAttachment"]] = relationship(
        "ChatMessageAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ChatMessageAttachment.created_at",
    )
    reads: Mapped[list["ChatMessageRead"]] = relationship(
        "ChatMessageRead",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ChatMessageRead.read_at",
    )
    forwarded_from_message: Mapped["ChatMessage | None"] = relationship(
        "ChatMessage",
        remote_side=[id],
        foreign_keys=[forwarded_from_message_id],
        uselist=False,
    )
    original_message: Mapped["ChatMessage | None"] = relationship(
        "ChatMessage",
        remote_side=[id],
        foreign_keys=[original_message_id],
        uselist=False,
    )

    def __repr__(self):
        return f"<ChatMessage id={self.id} chat={self.chat_id} sender={self.sender_id}>"
