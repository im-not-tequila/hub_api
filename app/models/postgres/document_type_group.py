from sqlalchemy import Integer, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class DocumentTypeGroup(PostgresBase, TimestampMixin):
    __tablename__ = 'document_type_groups'

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
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    document_types = relationship(
        "DocumentType",
        back_populates="document_type_group",
        cascade="all, delete-orphan"
    )

    roles: Mapped[list["RoleDocumentTypeGroup"]] = relationship(
        "RoleDocumentTypeGroup",
        back_populates="group",
        cascade="all, delete-orphan"
    )

    def __str__(self):
        return f"{self.id} - {self.name_ru}"

