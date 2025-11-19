from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.user.router import router as user_router
from app.api.v1.doc.router import router as docs_router
from app.api.v1.notification.router import router as notification_router
from app.api.v1.work_tabel.router import router as work_tabel_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/v1/auth", tags=["Auth"])

api_router.include_router(user_router, prefix="/v1/user", tags=["User"])

api_router.include_router(docs_router, prefix="/v1/doc", tags=["Document"])

api_router.include_router(notification_router, prefix="/v1/notifications", tags=["Notification"])

api_router.include_router(work_tabel_router, prefix="/v1/work-tabel", tags=["WorkTabel"])
