from __future__ import annotations

import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.migrate_user import MigrateUserMysqlToPostgres
from app.dao.mysql import MonitoringDAO
from app.dao.postgres import MonitoringPostgresDAO
from app.models.postgres.employee_custom_schedule import EmployeeCustomSchedule
from app.services.monitoring.constants import (
    ARRIVAL_GRACE_MINUTES,
    DEFAULT_SHIFT_END_TIME,
    DEFAULT_SHIFT_START_TIME,
)


class MonitoringServiceBase:
    def __init__(
        self,
        *,
        session_nitro: AsyncSession | None = None,
        session_perco: AsyncSession | None = None,
        session_postgres: AsyncSession | None = None,
    ):
        self.session_nitro = session_nitro
        self.session_perco = session_perco
        self.session_postgres = session_postgres

    def _monitoring_dao(self) -> MonitoringDAO:
        if self.session_nitro is None and self.session_perco is None:
            raise RuntimeError("Nitro or Perco session is required")
        return MonitoringDAO(
            session_nitro=self.session_nitro,
            session_perco=self.session_perco,
        )

    def _monitoring_postgres_dao(self) -> MonitoringPostgresDAO:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        return MonitoringPostgresDAO(self.session_postgres)

    async def _platonus_to_user_id_map(self, platonus_ids: list[int]) -> dict[int, int]:
        """
        Сопоставляет TutorID (platonus_id) с users.id только для сотрудников (is_student=False).
        Данные мониторинга — из nitro.tutors; студентов не ищем и не создаём.
        """
        if self.session_nitro is None or self.session_postgres is None:
            raise RuntimeError("Nitro and Postgres sessions are required for user_id resolution")
        unique = list(dict.fromkeys(pid for pid in platonus_ids if pid is not None))
        if not unique:
            return {}
        mapping = await self._monitoring_postgres_dao().get_staff_user_mapping(unique)
        missing = [pid for pid in unique if pid not in mapping]
        if missing:
            created = await MigrateUserMysqlToPostgres(
                session_nitro=self.session_nitro,
                session_postgres=self.session_postgres,
            ).migrate_tutors_by_ids(missing)
            mapping.update(created)
        return mapping

    async def _user_id_for_tutor(self, platonus_id: int) -> int | None:
        m = await self._platonus_to_user_id_map([platonus_id])
        return m.get(platonus_id)

    async def _load_active_staff_rows(self) -> list[dict[str, object]]:
        return await self._monitoring_dao().get_active_staff_rows()

    async def _load_active_academic_rows(self) -> list[dict[str, object]]:
        return await self._monitoring_dao().get_active_academic_rows()

    async def _resolve_staff_user_id_or_404(self, *, platonus_id: int) -> int:
        user_id = await self._user_id_for_tutor(platonus_id)
        if user_id is None:
            raise HTTPException(status_code=404, detail="Employee user not found")
        return user_id

    async def _load_custom_schedules(
        self,
        *,
        user_ids: list[int],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> dict[int, list[EmployeeCustomSchedule]]:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        unique_user_ids = sorted({uid for uid in user_ids if uid is not None})
        return await self._monitoring_postgres_dao().get_custom_schedules(
            user_ids=unique_user_ids,
            start_date=start_date,
            end_date=end_date,
        )

    @staticmethod
    def _calculate_arrival_status(
        *,
        first_in_datetime: datetime.datetime | None,
        shift_start_time: datetime.time,
    ) -> str | None:
        if first_in_datetime is None:
            return None
        first_in_time = first_in_datetime.time()
        shift_start_dt = datetime.datetime.combine(first_in_datetime.date(), shift_start_time)
        grace_deadline = (shift_start_dt + datetime.timedelta(minutes=ARRIVAL_GRACE_MINUTES)).time()

        if first_in_time < shift_start_time:
            return "BEFORE_SHIFT_START"
        if first_in_time <= grace_deadline:
            return "WITHIN_GRACE_PERIOD"
        return "LATE"

    @staticmethod
    def _resolve_schedule(
        *,
        user_id: int | None,
        access_date: datetime.date,
        schedules_by_user: dict[int, list[EmployeeCustomSchedule]],
    ) -> tuple[datetime.time, datetime.time, bool]:
        if user_id is None:
            return DEFAULT_SHIFT_START_TIME, DEFAULT_SHIFT_END_TIME, False
        for schedule in schedules_by_user.get(user_id, []):
            if schedule.start_date <= access_date and (
                schedule.end_date is None or schedule.end_date >= access_date
            ):
                return schedule.work_start_time, schedule.work_end_time, True
        return DEFAULT_SHIFT_START_TIME, DEFAULT_SHIFT_END_TIME, False

    @staticmethod
    def _format_time(value: datetime.time) -> str:
        return value.strftime("%H:%M")

    @staticmethod
    def _iter_weekdays(start_date: datetime.date, end_date: datetime.date) -> list[datetime.date]:
        days: list[datetime.date] = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                days.append(current)
            current += datetime.timedelta(days=1)
        return days
