from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.v1.auth.router import router as auth_router
from app.api.v1.user.router import router as user_router
from app.api.v1.doc.router import router as docs_router
from app.api.v1.notification.router import router as notification_router
from app.api.v1.work_tabel.router import router as work_tabel_router


GOOGLE_PLAY_URL = "https://play.google.com/store/apps/details?id=com.nureek2001.ShakarimApp"
APP_STORE_URL = "https://apps.apple.com/kz/app/shakarim-university/id6753332756"
DEFAULT_URL = "https://new.hub.shakarim.kz/"

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/v1/auth", tags=["Auth"])

api_router.include_router(user_router, prefix="/v1/user", tags=["User"])

api_router.include_router(docs_router, prefix="/v1/doc", tags=["Document"])

api_router.include_router(notification_router, prefix="/v1/notifications", tags=["Notification"])

api_router.include_router(work_tabel_router, prefix="/v1/work-tabel", tags=["WorkTabel"])


@api_router.get("/mobile-app")
async def download(request: Request):
    user_agent = request.headers.get("User-Agent", "").lower()

    if "android" in user_agent:
        return RedirectResponse(GOOGLE_PLAY_URL)

    # iOS определяется по iPhone/iPad или Safari на iOS
    if "iphone" in user_agent or "ipad" in user_agent or "ipod" in user_agent:
        return RedirectResponse(APP_STORE_URL)

    # Остальные (ПК, неизвестные устройства)
    return RedirectResponse(DEFAULT_URL)
