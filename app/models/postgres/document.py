from sqlalchemy import Integer, Text, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase


class Document(PostgresBase):
    __tablename__ = 'documents'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    author_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True
    )

    recipient_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True
    )

    document_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('document_types.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True
    )

    document_type = relationship("DocumentType", backref="documents")

    name: Mapped[str] = mapped_column(Text, nullable=False)
    sigex_id: Mapped[str] = mapped_column(Text, nullable=True)
    is_all_signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    signed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


