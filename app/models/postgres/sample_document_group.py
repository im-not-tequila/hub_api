from sqlalchemy import Integer, String, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class SampleDocumentGroup(PostgresBase, TimestampMixin):
    __tablename__ = 'sample_document_groups'

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

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true")
    )

