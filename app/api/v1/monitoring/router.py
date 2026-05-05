from fastapi import APIRouter

from app.api.v1.monitoring.employees.router import router as employees_router

router = APIRouter()
router.include_router(employees_router, prefix="/employees")

