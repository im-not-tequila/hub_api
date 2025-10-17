from enum import Enum
from datetime import datetime, timezone

from sqlalchemy import Integer, DateTime, func, ForeignKey, String, Enum as sqlalchemyEnum, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class DocumentStatus(Enum):
    PENDING = "pending"
    SIGNED = "signed"
    REJECTED = "cancelled"
    ON_EXECUTION = "on_execution"
    EXECUTED = "executed"
    REVOKED = "revoked"


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

    status: Mapped[DocumentStatus] = mapped_column(
        sqlalchemyEnum(DocumentStatus, name="document_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default = DocumentStatus.PENDING,
    )

    status_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    hidden_by_users: Mapped[list["HiddenDocument"]] = relationship(
        "HiddenDocument",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __str__(self):
        return f"{self.id} - {self.name}"

    def __repr__(self):
        return (
            f"<Document "
            f"id={self.id} "
            f"name={self.name} "
            f"author_id={self.author_id} "
            f"recipient_id={self.recipient_id} "
            f"status={self.status}>"
        )


@event.listens_for(Document.status, "set")
def receive_set(target, value, oldvalue, initiator):
    if value != oldvalue:
        target.status_updated_at = datetime.now(timezone.utc)
