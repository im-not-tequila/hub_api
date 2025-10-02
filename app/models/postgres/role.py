from sqlalchemy import Integer, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
# from app.models.postgres.user_role import UserRole
from .timestamp_mixin import TimestampMixin
from app.models.postgres.role_document_type_group import RoleDocumentTypeGroup


class Role(PostgresBase, TimestampMixin):
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    name_ru: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    name_kz: Mapped[str] = mapped_column(
        String(100),
        nullable = False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan"
    )

    document_type_groups: Mapped[list["RoleDocumentTypeGroup"]] = relationship(
        "RoleDocumentTypeGroup",
        back_populates="role",
        cascade="all, delete-orphan"
    )

    def __str__(self):
        return f"{self.id} - {self.name_ru}"
