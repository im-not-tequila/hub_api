from sqlalchemy import Integer, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres_connection import PostgresBase


class Approver(PostgresBase):
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

    approver_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True
    )

    is_signed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    signed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
        default=None
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


