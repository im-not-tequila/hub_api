from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Path as PathParam, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.monitoring.employees.academic.router import router as academic_router
from app.api.v1.monitoring.employees.staff.router import router as staff_router
from app.api.v1.monitoring.schemas import EmployeeAccessLogItem
from app.db.session import get_perco_session
from app.services.monitoring import MonitoringService

router = APIRouter()

router.include_router(staff_router, prefix="/staff")
router.include_router(academic_router, prefix="/academic")


@router.get(path="/{id}/access-logs", response_model=list[EmployeeAccessLogItem])
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
