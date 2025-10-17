from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase


class HiddenDocument(PostgresBase):
    __tablename__ = 'hidden_documents'
    __table_args__ = (
        UniqueConstraint('user_id', 'document_id', name='uix_user_document'),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('documents.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    hidden_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="hidden_documents")
    document = relationship("Document", back_populates="hidden_by_users")
