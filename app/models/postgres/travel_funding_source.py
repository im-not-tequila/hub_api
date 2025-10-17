from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class TravelFundingSource(PostgresBase, TimestampMixin):
    __tablename__ = 'travel_funding_sources'

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
        default=True
    )

    def __str__(self):
        return f"{self.id} - {self.name_ru}"

    def __repr__(self):
        return (
            f"<TravelFundingSource "
            f"id={self.id} "
            f"name_ru={self.name_ru} "
            f"name_kz={self.name_kz} "
            f"is_active={self.is_active}>"
        )
