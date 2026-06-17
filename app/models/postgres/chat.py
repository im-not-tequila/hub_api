import enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, Integer, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin

if TYPE_CHECKING:
    from app.models.postgres.chat_message import ChatMessage
    from app.models.postgres.chat_participant import ChatParticipant


class ChatType(enum.Enum):
    DIRECT = "direct"
    GROUP = "group"


class Chat(PostgresBase, TimestampMixin):
    __tablename__ = 'chats'
    __table_args__ = (
        Index('ix_chats_user1_id', 'user1_id'),
        Index('ix_chats_user2_id', 'user2_id'),
        Index('ix_chats_type', 'type'),
        Index(
            'uq_direct_chat_pair',
            'user1_id',
            'user2_id',
            unique=True,
            postgresql_where=text("type = 'direct'"),
        ),
        CheckConstraint(
            """
            (
                type = 'direct'
                AND user1_id IS NOT NULL
                AND user2_id IS NOT NULL
                AND user1_id <> user2_id
            )
            OR
            (
                type = 'group'
                AND user1_id IS NULL
                AND user2_id IS NULL
                AND title IS NOT NULL
                AND creator_user_id IS NOT NULL
            )
            """,
            name="ck_chats_direct_or_group_shape",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    type: Mapped[ChatType] = mapped_column(
        Enum(ChatType, name="chat_type", values_callable=lambda x: [e.value for e in x]),
        default=ChatType.DIRECT,
        server_default=ChatType.DIRECT.value,
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    creator_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )

    user1_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True
    )
    user2_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ChatMessage.created_at",
    )
    participants: Mapped[list["ChatParticipant"]] = relationship(
        "ChatParticipant",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self):
        return (
            f"<Chat id={self.id} type={self.type.value} "
            f"user1={self.user1_id} user2={self.user2_id}>"
        )
