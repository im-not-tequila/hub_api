from sqlalchemy import ForeignKey, Boolean, String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class Notification(PostgresBase, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(String)
    sender_user_id: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    sender_name: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    other_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # user = relationship("User", back_populates="notifications")
