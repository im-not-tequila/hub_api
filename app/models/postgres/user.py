from sqlalchemy import Integer, Text, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
# from app.models.postgres import Role, UserInfo, user_roles
from app.models.postgres.user_role import user_roles


class User(PostgresBase):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platonus_id: Mapped[int] = mapped_column(Integer, nullable=False)
    is_student: Mapped[bool] = mapped_column(Boolean, nullable=False)
    bin_number: Mapped[str] = mapped_column(Text, nullable=True)

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

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin"
    )

    info: Mapped["UserInfo"] = relationship(
        "UserInfo",
        back_populates="user",
        uselist=False,  # уберите, если нужна связь один-ко-многим
        cascade="all, delete-orphan"
    )

