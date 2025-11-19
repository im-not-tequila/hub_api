from sqlalchemy import Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class CustomDocumentTemplate(PostgresBase, TimestampMixin):
    __tablename__ = 'custom_document_templates'

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    document_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('document_types.id', ondelete='CASCADE'),
    )

    data_ru: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    data_kz: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    data_en: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
