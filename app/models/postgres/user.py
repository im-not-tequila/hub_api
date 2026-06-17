from typing import TYPE_CHECKING

from sqlalchemy import Integer, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
# from app.models.postgres.user_role import UserRole
# from app.models.postgres.user_info import UserInfo
from .timestamp_mixin import TimestampMixin

if TYPE_CHECKING:
    from app.models.postgres.calendar_event_manager import CalendarEventManager
    from app.models.postgres.chat_participant import ChatParticipant
    from app.models.postgres.employee_custom_schedule import EmployeeCustomSchedule
    from app.models.postgres.hidden_document import HiddenDocument
    from app.models.postgres.user_info import UserInfo
    from app.models.postgres.user_role import UserRole


class User(PostgresBase, TimestampMixin):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    platonus_id: Mapped[int] = mapped_column(
        Integer,
        nullable=True
    )

    is_student: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )

    bin_number: Mapped[str] = mapped_column(
        String(12),
        nullable=True,
        default=None,
    )

    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy = "selectin"
    )

    info: Mapped["UserInfo"] = relationship(
        "UserInfo",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin"
    )

    hidden_documents: Mapped[list["HiddenDocument"]] = relationship(
        "HiddenDocument",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    created_calendar_events: Mapped[list["CalendarEventManager"]] = relationship(
        "CalendarEventManager",
        back_populates="creator_user",
        foreign_keys="CalendarEventManager.creator_user_id",
        lazy="selectin",
    )

    custom_schedules: Mapped[list["EmployeeCustomSchedule"]] = relationship(
        "EmployeeCustomSchedule",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    chat_participations: Mapped[list["ChatParticipant"]] = relationship(
        "ChatParticipant",
        foreign_keys="ChatParticipant.user_id",
        lazy="selectin",
    )

    def __str__(self):
        if self.is_student:
            role = 'student'
        else:
            role = 'tutor'

        return f"{self.platonus_id} ({role})"

    def __repr__(self):
        return f"<User id={self.id} platonus_id={self.platonus_id} is_student={self.is_student}>"


