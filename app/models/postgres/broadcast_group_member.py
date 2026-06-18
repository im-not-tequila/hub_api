from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey, UniqueConstraint, Index, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase

if TYPE_CHECKING:
    from app.models.postgres.broadcast_group import BroadcastGroup
    from app.models.postgres.user import User


class BroadcastGroupMember(PostgresBase):
    __tablename__ = "broadcast_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_broadcast_group_members_group_user"),
        Index("ix_broadcast_group_members_group_id", "group_id"),
        Index("ix_broadcast_group_members_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("broadcast_groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    added_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    group: Mapped["BroadcastGroup"] = relationship(
        "BroadcastGroup", back_populates="members"
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    def __repr__(self):
        return f"<BroadcastGroupMember group={self.group_id} user={self.user_id}>"
