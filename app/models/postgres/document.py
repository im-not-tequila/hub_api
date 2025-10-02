from datetime import datetime

from sqlalchemy import Integer, Boolean, DateTime, func, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class Document(PostgresBase, TimestampMixin):
    __tablename__ = 'documents'

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    recipient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    document_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('document_types.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    document_type = relationship(
        "DocumentType",
        backref="documents",
        lazy="selectin"
    )

    author_user = relationship(
        "User",
        foreign_keys=[author_id],
        backref="authored_documents",
        lazy="joined"
    )

    recipient_user = relationship(
        "User",
        foreign_keys=[recipient_id],
        backref="received_documents",
        lazy="joined"
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    sigex_id: Mapped[str] = mapped_column(
        String(16),
        nullable=True,
        index=True
    )

    is_all_signed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    all_signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True
    )

    is_cancelled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    def __str__(self):
        return f"{self.id} - {self.name}"

    def __repr__(self):
        return f"<Document id={self.id} name={self.name} author_id={self.author_id} recipient_id={self.recipient_id}>"

