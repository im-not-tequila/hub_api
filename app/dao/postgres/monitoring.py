import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres import User
from app.models.postgres.employee_custom_schedule import EmployeeCustomSchedule


class MonitoringPostgresDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_staff_user_mapping(self, platonus_ids: list[int]) -> dict[int, int]:
        if not platonus_ids:
            return {}
        stmt = (
            select(User.id, User.platonus_id)
            .where(User.platonus_id.in_(platonus_ids))
            .where(User.is_student.is_(False))
        )
        result = await self.session.execute(stmt)
        mapping: dict[int, int] = {}
        for user_id, platonus_id in result.all():
            if platonus_id is None:
                continue
            mapping[int(platonus_id)] = int(user_id)
        return mapping

    async def get_custom_schedules(
        self,
        *,
        user_ids: list[int],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> dict[int, list[EmployeeCustomSchedule]]:
        if not user_ids:
            return {}
        stmt = (
            select(EmployeeCustomSchedule)
            .where(EmployeeCustomSchedule.user_id.in_(user_ids))
            .where(EmployeeCustomSchedule.start_date <= end_date)
            .where(
                or_(
                    EmployeeCustomSchedule.end_date.is_(None),
                    EmployeeCustomSchedule.end_date >= start_date,
                )
            )
            .order_by(
                EmployeeCustomSchedule.user_id.asc(),
                EmployeeCustomSchedule.start_date.desc(),
                EmployeeCustomSchedule.created_at.desc(),
            )
        )
        result = await self.session.execute(stmt)
        schedules: dict[int, list[EmployeeCustomSchedule]] = {}
        for schedule in result.scalars().all():
            schedules.setdefault(int(schedule.user_id), []).append(schedule)
        return schedules

    async def get_user_schedules(self, user_id: int) -> list[EmployeeCustomSchedule]:
        stmt = (
            select(EmployeeCustomSchedule)
            .where(EmployeeCustomSchedule.user_id == user_id)
            .order_by(
                EmployeeCustomSchedule.start_date.desc(),
                EmployeeCustomSchedule.id.desc(),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_user_schedule_by_id(
        self,
        *,
        user_id: int,
        schedule_id: int,
    ) -> EmployeeCustomSchedule | None:
        stmt = (
            select(EmployeeCustomSchedule)
            .where(EmployeeCustomSchedule.id == schedule_id)
            .where(EmployeeCustomSchedule.user_id == user_id)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_schedule(
        self,
        *,
        user_id: int,
        start_date: datetime.date,
        end_date: datetime.date | None,
        work_start_time: datetime.time,
        work_end_time: datetime.time,
    ) -> EmployeeCustomSchedule:
        schedule = EmployeeCustomSchedule(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            work_start_time=work_start_time,
            work_end_time=work_end_time,
        )
        self.session.add(schedule)
        await self.session.commit()
        await self.session.refresh(schedule)
        return schedule

    async def update_schedule(
        self,
        *,
        schedule: EmployeeCustomSchedule,
        start_date: datetime.date,
        end_date: datetime.date | None,
        work_start_time: datetime.time,
        work_end_time: datetime.time,
    ) -> EmployeeCustomSchedule:
        schedule.start_date = start_date
        schedule.end_date = end_date
        schedule.work_start_time = work_start_time
        schedule.work_end_time = work_end_time
        await self.session.commit()
        await self.session.refresh(schedule)
        return schedule

    async def delete_schedule(self, schedule: EmployeeCustomSchedule) -> None:
        await self.session.delete(schedule)
        await self.session.commit()
