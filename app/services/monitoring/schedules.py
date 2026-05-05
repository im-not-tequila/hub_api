from __future__ import annotations

from fastapi import HTTPException

from app.api.v1.monitoring.schemas import EmployeeWorkScheduleCreateUpdate, EmployeeWorkScheduleItem


class MonitoringSchedulesMixin:
    async def list_employee_work_schedules(
        self,
        *,
        platonus_id: int,
    ) -> list[EmployeeWorkScheduleItem]:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        user_id = await self._resolve_staff_user_id_or_404(platonus_id=platonus_id)
        rows = await self._monitoring_postgres_dao().get_user_schedules(user_id)
        return [
            EmployeeWorkScheduleItem.model_validate(
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "start_date": row.start_date,
                    "end_date": row.end_date,
                    "work_start_time": row.work_start_time,
                    "work_end_time": row.work_end_time,
                }
            )
            for row in rows
        ]

    async def create_employee_work_schedule(
        self,
        *,
        platonus_id: int,
        payload: EmployeeWorkScheduleCreateUpdate,
    ) -> EmployeeWorkScheduleItem:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        user_id = await self._resolve_staff_user_id_or_404(platonus_id=platonus_id)
        if payload.end_date is not None and payload.end_date < payload.start_date:
            raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")

        schedule = await self._monitoring_postgres_dao().create_schedule(
            user_id=user_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            work_start_time=payload.work_start_time,
            work_end_time=payload.work_end_time,
        )
        return EmployeeWorkScheduleItem.model_validate(
            {
                "id": schedule.id,
                "user_id": schedule.user_id,
                "start_date": schedule.start_date,
                "end_date": schedule.end_date,
                "work_start_time": schedule.work_start_time,
                "work_end_time": schedule.work_end_time,
            }
        )

    async def update_employee_work_schedule(
        self,
        *,
        platonus_id: int,
        schedule_id: int,
        payload: EmployeeWorkScheduleCreateUpdate,
    ) -> EmployeeWorkScheduleItem:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        user_id = await self._resolve_staff_user_id_or_404(platonus_id=platonus_id)
        if payload.end_date is not None and payload.end_date < payload.start_date:
            raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")

        schedule = await self._monitoring_postgres_dao().get_user_schedule_by_id(
            user_id=user_id,
            schedule_id=schedule_id,
        )
        if schedule is None:
            raise HTTPException(status_code=404, detail="Work schedule not found")

        schedule = await self._monitoring_postgres_dao().update_schedule(
            schedule=schedule,
            start_date=payload.start_date,
            end_date=payload.end_date,
            work_start_time=payload.work_start_time,
            work_end_time=payload.work_end_time,
        )
        return EmployeeWorkScheduleItem.model_validate(
            {
                "id": schedule.id,
                "user_id": schedule.user_id,
                "start_date": schedule.start_date,
                "end_date": schedule.end_date,
                "work_start_time": schedule.work_start_time,
                "work_end_time": schedule.work_end_time,
            }
        )

    async def delete_employee_work_schedule(
        self,
        *,
        platonus_id: int,
        schedule_id: int,
    ) -> None:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        user_id = await self._resolve_staff_user_id_or_404(platonus_id=platonus_id)
        schedule = await self._monitoring_postgres_dao().get_user_schedule_by_id(
            user_id=user_id,
            schedule_id=schedule_id,
        )
        if schedule is None:
            raise HTTPException(status_code=404, detail="Work schedule not found")

        await self._monitoring_postgres_dao().delete_schedule(schedule)
