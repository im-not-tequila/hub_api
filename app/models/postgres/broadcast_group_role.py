from typing import TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase

if TYPE_CHECKING:
    from app.models.postgres.broadcast_group import BroadcastGroup
    from app.models.postgres.role import Role


class BroadcastGroupRole(PostgresBase):
    """Роль, имеющая доступ к отправке рассылки через данную группу."""

    __tablename__ = "broadcast_group_roles"
    __table_args__ = (
        UniqueConstraint("group_id", "role_id", name="uq_broadcast_group_roles_group_role"),
        Index("ix_broadcast_group_roles_group_id", "group_id"),
        Index("ix_broadcast_group_roles_role_id", "role_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("broadcast_groups.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )

    group: Mapped["BroadcastGroup"] = relationship(
        "BroadcastGroup", back_populates="allowed_roles"
    )
    role: Mapped["Role"] = relationship(
        "Role",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<BroadcastGroupRole group={self.group_id} role={self.role_id}>"
