from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
# from app.models.postgres.user import User
# from app.models.postgres.role import Role
from .timestamp_mixin import TimestampMixin


class UserRole(PostgresBase, TimestampMixin):
    __tablename__ = 'user_roles'

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        primary_key=True
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey('roles.id', ondelete='CASCADE'),
        primary_key=True
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_roles"
    )

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="user_roles"
    )

    def __repr__(self):
        return f"<UserRole user_id={self.user_id} role_id={self.role_id}>"

