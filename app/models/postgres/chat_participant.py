import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class ChatParticipantRole(enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class ChatParticipant(PostgresBase, TimestampMixin):
    __tablename__ = "chat_participants"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_chat_participants_chat_user"),
        Index("ix_chat_participants_chat_id", "chat_id"),
        Index("ix_chat_participants_user_id", "user_id"),
        Index("ix_chat_participants_role", "role"),
        Index("ix_chat_participants_is_active", "is_active"),
        Index("ix_chat_participants_removed_by_user_id", "removed_by_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ChatParticipantRole] = mapped_column(
        Enum(
            ChatParticipantRole,
            name="chat_participant_role",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ChatParticipantRole.MEMBER,
        server_default=ChatParticipantRole.MEMBER.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    added_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    removed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chat: Mapped["Chat"] = relationship("Chat", back_populates="participants")

    def __repr__(self):
        return (
            f"<ChatParticipant id={self.id} chat={self.chat_id} user={self.user_id} "
            f"role={self.role.value} active={self.is_active}>"
        )
