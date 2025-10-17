from sqlalchemy import Integer, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class DocumentType(PostgresBase, TimestampMixin):
    __tablename__ = 'document_types'

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

    document_type_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('document_type_groups.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True
    )

    document_type_group = relationship(
        "DocumentTypeGroup",
        back_populates="document_types",
        lazy="joined"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    def __str__(self):
        return f"{self.id} - {self.name_ru}"

