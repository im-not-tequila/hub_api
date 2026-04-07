from typing import TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey, String, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin

if TYPE_CHECKING:
    from .normative_document import NormativeDocument
    from .normative_document_category import NormativeDocumentCategory


class NormativeDocumentSubcategory(PostgresBase, TimestampMixin):
    __tablename__ = 'normative_document_subcategories'

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

    normative_document_category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('normative_document_categories.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    category: Mapped["NormativeDocumentCategory"] = relationship(
        "NormativeDocumentCategory",
        back_populates="subcategories",
        lazy="joined"
    )

    documents: Mapped[list["NormativeDocument"]] = relationship(
        "NormativeDocument",
        back_populates="subcategory",
        cascade="all, delete-orphan"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true")
    )
