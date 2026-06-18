from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin

if TYPE_CHECKING:
    from app.models.postgres.broadcast_group_member import BroadcastGroupMember
    from app.models.postgres.broadcast_group_role import BroadcastGroupRole
    from app.models.postgres.user import User


class BroadcastGroup(PostgresBase, TimestampMixin):
    __tablename__ = "broadcast_groups"
    __table_args__ = (
        Index("ix_broadcast_groups_created_by_user_id", "created_by_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    members: Mapped[list["BroadcastGroupMember"]] = relationship(
        "BroadcastGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    allowed_roles: Mapped[list["BroadcastGroupRole"]] = relationship(
        "BroadcastGroupRole",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    creator: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
        lazy="selectin",
    )

    def __repr__(self):
        return f"<BroadcastGroup id={self.id} name={self.name!r}>"
