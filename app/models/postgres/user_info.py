from sqlalchemy import Integer, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.postgres_connection import PostgresBase
from app.models.postgres import User
from .timestamp_mixin import TimestampMixin


class UserInfo(PostgresBase, TimestampMixin):
    __tablename__ = 'users_info'

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,  # сделайте False, если допускается несколько UserInfo на одного User
        index=True
    )

    lastname: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    firstname: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    patronymic: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    iin_number: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        index=True
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="info",
        lazy="selectin",
        passive_deletes=True
    )

    @validates('iin_number')
    def validate_iin(self, key, value):
        if len(value) != 12 or not value.isdigit():
            raise ValueError("IIN must be exactly 12 digits")
        return value

