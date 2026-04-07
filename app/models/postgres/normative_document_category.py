from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin

if TYPE_CHECKING:
    from .normative_document_subcategory import NormativeDocumentSubcategory


class NormativeDocumentCategory(PostgresBase, TimestampMixin):
    __tablename__ = 'normative_document_categories'

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    name_ru: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    name_kz: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    name_en: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true")
    )

    subcategories: Mapped[list["NormativeDocumentSubcategory"]] = relationship(
        "NormativeDocumentSubcategory",
        back_populates="category",
        cascade="all, delete-orphan"
    )
