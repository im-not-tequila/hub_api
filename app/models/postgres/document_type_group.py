from sqlalchemy import Integer, Text, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres_connection import PostgresBase


class DocumentTypeGroup(PostgresBase):
    __tablename__ = 'document_type_groups'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_ru: Mapped[str] = mapped_column(Text, nullable=False)
    name_kz: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

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


