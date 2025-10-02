import enum

from datetime import datetime

from sqlalchemy import Integer, Boolean, DateTime, func, ForeignKey, Enum, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class ApproverStatus(enum.Enum):
    PENDING = "pending"
    SIGNED = "signed"
    REJECTED = "cancelled"


class Approver(PostgresBase, TimestampMixin):
    __tablename__ = 'approvers'

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('documents.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True
    )

    document = relationship(
        "Document",
        foreign_keys=[document_id],
        backref="approvers",
        lazy="joined"
    )

    resolution: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        default=None
    )

    approver_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True
    )

    approver_user = relationship(
        "User",
        foreign_keys=[approver_id],
        backref="approver_documents",
        lazy="joined"
    )

    is_recipient: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    status: Mapped[ApproverStatus] = mapped_column(
        Enum(ApproverStatus, name="approver_status", values_callable=lambda x: [e.value for e in x]),
        default=ApproverStatus.PENDING,
        nullable=False
    )

    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
        default=None
    )

    __table_args__ = (
        UniqueConstraint("document_id", "approver_id", name="uq_document_approver"),
    )


