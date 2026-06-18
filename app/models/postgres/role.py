from sqlalchemy import Integer, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

from app.db.postgres_connection import PostgresBase
# from app.models.postgres.user_role import UserRole
from .timestamp_mixin import TimestampMixin
from app.models.postgres.role_document_type_group import RoleDocumentTypeGroup
from app.models.postgres.role_sidebar_section import RoleSidebarSection


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
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    document_type_groups: Mapped[list["RoleDocumentTypeGroup"]] = relationship(
        "RoleDocumentTypeGroup",
        back_populates="role",
        cascade="all, delete-orphan"
    )

    sidebar_sections: Mapped[list["RoleSidebarSection"]] = relationship(
        "RoleSidebarSection",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __str__(self):
        return f"{self.id} - {self.name_ru}"

    @staticmethod
    def active_roles(session: Session):
        return session.query(Role).filter(Role.is_active == True).order_by(Role.name_ru)

