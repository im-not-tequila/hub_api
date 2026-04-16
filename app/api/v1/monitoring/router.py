from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Path as PathParam, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_nitro_session, get_perco_session, get_postgres_session
from app.api.v1.monitoring.schemas import (
    EmployeePunctualityStatsItem,
    EmployeeWorkScheduleCreateUpdate,
    EmployeeWorkScheduleItem,
    EmployeeAccessLogItem,
    TutorDetailItem,
    TutorFirstInItem,
    TutorListItem,
)
from app.services.monitoring import AbsenceLang, MonitoringService


router = APIRouter()


@router.get(path="/employees/staff/list/active", response_model=list[TutorListItem])
async def list_employees_staff(
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
    lang: AbsenceLang = Query("ru", description="Language: ru/kz/en"),
) -> list[TutorListItem]:
    return await MonitoringService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).list_employees_staff(
        lang=lang
    )


@router.get(path="/employees/staff/list/active/punctuality/stats", response_model=list[EmployeePunctualityStatsItem])
async def list_active_employees_punctuality_stats(
    start_date: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
    session_perco: AsyncSession = Depends(get_perco_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> list[EmployeePunctualityStatsItem]:
    return await MonitoringService(
        session_perco=session_perco,
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).list_active_employees_punctuality_stats(
        start_date=start_date,
        end_date=end_date,
    )


@router.get(path="/employees/staff/list/active/excel")
async def export_employees_staff_excel(
    structural_subdivision_id: int | None = Query(None, description="Filter by structural subdivision ID"),
    search: str | None = Query(None, description="Search by full name, subdivision or position"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> Response:
    service = MonitoringService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    )
    content = await service.export_employees_staff_excel(
        structural_subdivision_id=structural_subdivision_id,
        search=search,
    )
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    headers = {
        "Content-Disposition": f'attachment; filename="monitoring_staff_{timestamp}.xls"',
    }
    return Response(
        content=content,
        media_type="application/vnd.ms-excel",
        headers=headers,
    )


@router.get(path="/employees/staff/{id}", response_model=TutorDetailItem)
async def get_employee_staff(
    platonus_id: int = PathParam(..., alias="id", description="TutorID"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
    lang: AbsenceLang = Query("ru", description="Language: ru/kz/en"),
) -> TutorDetailItem:
    return await MonitoringService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).get_employee_staff(
        platonus_id=platonus_id,
        lang=lang,
    )


@router.get(path="/employees/staff/{id}/access-logs", response_model=list[EmployeeAccessLogItem])
async def list_employee_access_logs(
    platonus_id: int = PathParam(..., alias="id", description="Perco personid"),
    start_date: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
    session_perco: AsyncSession = Depends(get_perco_session),
) -> list[EmployeeAccessLogItem]:
    return await MonitoringService(session_perco=session_perco).list_employee_access_logs(
        platonus_id=platonus_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(path="/employees/staff/list/punctuality", response_model=list[TutorFirstInItem])
async def list_tutors_punctuality(
    date: datetime.date | None = Query(None, description="Date (YYYY-MM-DD), default=today"),
    session_perco: AsyncSession = Depends(get_perco_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> list[TutorFirstInItem]:
    return await MonitoringService(
        session_perco=session_perco,
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).list_staff_punctuality(
        startdate=date,
        enddate=date,
    )


@router.get(path="/employees/staff/{id}/punctuality/stats", response_model=EmployeePunctualityStatsItem)
async def get_employee_punctuality_stats(
    platonus_id: int = PathParam(..., alias="id", description="TutorID"),
    start_date: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
    session_perco: AsyncSession = Depends(get_perco_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> EmployeePunctualityStatsItem:
    return await MonitoringService(
        session_perco=session_perco,
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).get_employee_punctuality_stats(
        platonus_id=platonus_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(path="/employees/staff/list/punctuality/excel")
async def export_tutors_punctuality_excel(
    startdate: datetime.date | None = Query(None, description="Start date (YYYY-MM-DD), default=today"),
    enddate: datetime.date | None = Query(None, description="End date (YYYY-MM-DD), default=today"),
    arrival_status: str | None = Query(None, description="Arrival status filter"),
    schedule_type: str | None = Query(None, description="Work schedule type filter"),
    perco_status_name: str | None = Query(None, description="PERCo status filter"),
    search: str | None = Query(None, description="Search filter"),
    session_perco: AsyncSession = Depends(get_perco_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> Response:
    content = await MonitoringService(
        session_perco=session_perco,
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).export_staff_punctuality_excel(
        startdate=startdate,
        enddate=enddate,
        arrival_status=arrival_status,
        schedule_type=schedule_type,
        perco_status_name=perco_status_name,
        search=search,
    )
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    headers = {
        "Content-Disposition": f'attachment; filename="monitoring_punctuality_{timestamp}.xls"',
    }
    return Response(
        content=content,
        media_type="application/vnd.ms-excel",
        headers=headers,
    )


@router.get(
    path="/employees/staff/{id}/work-schedules",
    response_model=list[EmployeeWorkScheduleItem],
)
async def list_employee_work_schedules(
    platonus_id: int = PathParam(..., alias="id", description="TutorID"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> list[EmployeeWorkScheduleItem]:
    return await MonitoringService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).list_employee_work_schedules(platonus_id=platonus_id)


@router.post(
    path="/employees/staff/{id}/work-schedules",
    response_model=EmployeeWorkScheduleItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_employee_work_schedule(
    payload: EmployeeWorkScheduleCreateUpdate,
    platonus_id: int = PathParam(..., alias="id", description="TutorID"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> EmployeeWorkScheduleItem:
    return await MonitoringService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).create_employee_work_schedule(
        platonus_id=platonus_id,
        payload=payload,
    )


@router.put(
    path="/employees/staff/{id}/work-schedules/{schedule_id}",
    response_model=EmployeeWorkScheduleItem,
)
async def update_employee_work_schedule(
    payload: EmployeeWorkScheduleCreateUpdate,
    platonus_id: int = PathParam(..., alias="id", description="TutorID"),
    schedule_id: int = PathParam(..., description="Work schedule ID"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> EmployeeWorkScheduleItem:
    return await MonitoringService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).update_employee_work_schedule(
        platonus_id=platonus_id,
        schedule_id=schedule_id,
        payload=payload,
    )


@router.delete(
    path="/employees/staff/{id}/work-schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_employee_work_schedule(
    platonus_id: int = PathParam(..., alias="id", description="TutorID"),
    schedule_id: int = PathParam(..., description="Work schedule ID"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> Response:
    await MonitoringService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).delete_employee_work_schedule(
        platonus_id=platonus_id,
        schedule_id=schedule_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

