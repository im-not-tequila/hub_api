from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase

if TYPE_CHECKING:
    from app.models.postgres.user import User


class CalendarEventPlace(PostgresBase):
    __tablename__ = "calendar_event_place"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name_kz: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    events: Mapped[list["CalendarEventManager"]] = relationship(
        "CalendarEventManager",
        back_populates="place",
        lazy="selectin",
    )

class CalendarEventType(PostgresBase):
    __tablename__ = "calendar_event_type"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name_kz: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    events: Mapped[list["CalendarEventManager"]] = relationship(
        "CalendarEventManager",
        back_populates="type",
        lazy="selectin",
    )


class CalendarEventManager(PostgresBase):
    __tablename__ = "calendar_event_manager"
    __table_args__ = (
        Index("ix_calendar_event_manager_creator_user_id", "creator_user_id"),
        Index("ix_calendar_event_manager_structural_subdivision_id", "structural_subdivision_id"),
        Index("ix_calendar_event_manager_place_id", "place_id"),
        Index("ix_calendar_event_manager_event_type_id", "event_type_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    creator_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    structural_subdivision_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    place_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("calendar_event_place.id"),
        nullable=False,
    )

    title_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    title_kz: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[str] = mapped_column(String(255), nullable=False)

    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_kz: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)

    needs_media_capture: Mapped[bool] = mapped_column(Boolean, nullable=False)

    event_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("calendar_event_type.id"),
        nullable=False,
    )

    contacts: Mapped[str | None] = mapped_column(String(255), nullable=True)
    needs_tech_support: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    creator_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[creator_user_id],
        back_populates="created_calendar_events",
        lazy="selectin",
    )
    place: Mapped["CalendarEventPlace"] = relationship(
        "CalendarEventPlace",
        foreign_keys=[place_id],
        back_populates="events",
        lazy="selectin",
    )
    type: Mapped["CalendarEventType"] = relationship(
        "CalendarEventType",
        foreign_keys=[event_type_id],
        back_populates="events",
        lazy="selectin",
    )



