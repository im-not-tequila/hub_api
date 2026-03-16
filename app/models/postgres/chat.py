from sqlalchemy import Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class Chat(PostgresBase, TimestampMixin):
    __tablename__ = 'chats'
    __table_args__ = (
        Index('ix_chats_user1_id', 'user1_id'),
        Index('ix_chats_user2_id', 'user2_id'),
        Index('uq_chat_pair', 'user1_id', 'user2_id', unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user1_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )
    user2_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ChatMessage.created_at",
    )

    def __repr__(self):
        return f"<Chat id={self.id} user1={self.user1_id} user2={self.user2_id}>"
