from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.core.settings import get_settings


router = APIRouter()


def _detect_platform(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if "android" in ua:
        return "android"
    if any(x in ua for x in ("iphone", "ipad", "ipod", "ios")):
        return "ios"
    return "unknown"


@router.get("/store")
async def store_redirect(request: Request):
    """
    Редирект в стор в зависимости от типа устройства (User-Agent).
    """
    settings = get_settings()
    platform = _detect_platform(request.headers.get("user-agent", ""))

    target_url = (
        settings.APP_STORE_APP_LINK
        if platform == "ios"
        else settings.GOOGLE_PLAY_APP_LINK
    )
    return RedirectResponse(url=target_url, status_code=307)

