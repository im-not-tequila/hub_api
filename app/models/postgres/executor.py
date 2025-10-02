import enum

from datetime import datetime

from sqlalchemy import Integer, DateTime, func, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class ExecutorStatus(enum.Enum):
    PENDING_EXECUTION = "pending_execution"
    COMPLETED = "completed"


class Executor(PostgresBase, TimestampMixin):
    __tablename__ = 'executors'

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
        backref="executors",
        lazy="joined"
    )

    executor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True
    )

    executor_user = relationship(
        "User",
        foreign_keys=[executor_id],
        backref="executor_documents",
        lazy="joined"
    )

    status: Mapped[ExecutorStatus] = mapped_column(
        Enum(ExecutorStatus, name="executor_status", values_callable=lambda x: [e.value for e in x]),
        default=ExecutorStatus.PENDING_EXECUTION,
        nullable=False
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
        default=None
    )

    __table_args__ = (
        UniqueConstraint("document_id", "executor_id", name="uq_document_executor"),
    )


