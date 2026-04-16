import datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class EmployeeCustomSchedule(PostgresBase, TimestampMixin):
    __tablename__ = "employee_custom_schedules"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_employee_custom_schedules_end_date_gte_start_date",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    start_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    end_date: Mapped[datetime.date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    work_start_time: Mapped[datetime.time] = mapped_column(
        Time,
        nullable=False,
    )

    work_end_time: Mapped[datetime.time] = mapped_column(
        Time,
        nullable=False,
    )
