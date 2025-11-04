from sqlalchemy import Integer, ForeignKey, String, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class SampleDocument(PostgresBase, TimestampMixin):
    __tablename__ = 'sample_documents'

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

    sample_document_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('sample_document_groups.id', ondelete='CASCADE'),
    )

    sample_document_group = relationship(
        "SampleDocumentGroup",
        backref="sample_documents",
        lazy="selectin"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true")
    )
