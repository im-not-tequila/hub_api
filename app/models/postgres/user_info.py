from sqlalchemy import Integer, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from app.models.postgres import User


class UserInfo(PostgresBase):
    __tablename__ = 'users_info'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,  # сделайте False, если допускается несколько UserInfo на одного User
        index=True
    )

    name: Mapped[str] = mapped_column(Text, nullable=True)
    surname: Mapped[str] = mapped_column(Text, nullable=True)
    given_name: Mapped[str] = mapped_column(Text, nullable=True)
    iin_number: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="info",
        lazy="selectin",
        passive_deletes=True
    )

