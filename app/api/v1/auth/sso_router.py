import secrets

from fastapi import APIRouter, Response, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.dao.postgres import UserDAO
from app.db.session import get_postgres_session, redis_client
from app.models.postgres.user import User
from app.services.auth_service import AuthService
from app.api.v1.auth.router import _set_auth_cookies

router = APIRouter()
settings = get_settings()

SSO_TOKEN_TTL = 60  # секунды — одноразовый токен живёт 60 секунд


class SsoTokenRequest(BaseModel):
    sso_secret: str
    platonus_id: int


class SsoTokenResponse(BaseModel):
    sso_token: str


class SsoLoginRequest(BaseModel):
    sso_token: str


@router.post(
    "/sso/token",
    response_model=SsoTokenResponse,
    summary="Генерация одноразового SSO токена (вызывается PHP-проектом)",
)
async def generate_sso_token(
    data: SsoTokenRequest,
    session: AsyncSession = Depends(get_postgres_session),
):
    """
    PHP-проект вызывает этот endpoint server-to-server.
    Передаёт sso_secret (общий секрет) и platonus_id пользователя.
    Получает одноразовый sso_token, который живёт 60 секунд.
    """
    if not settings.SSO_SECRET or data.sso_secret != settings.SSO_SECRET:
        raise HTTPException(status_code=403, detail="Invalid SSO secret")

    user = await UserDAO(session).get_one_or_none(
        filters={User.platonus_id: data.platonus_id}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = secrets.token_urlsafe(32)
    await redis_client.setex(f"sso:{token}", SSO_TOKEN_TTL, str(user.id))

    return SsoTokenResponse(sso_token=token)


@router.post(
    "/sso/login",
    summary="Обмен SSO токена на auth cookies (вызывается iframe Vue-приложения)",
)
async def sso_login(
    data: SsoLoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_postgres_session),
):
    """
    Vue iframe вызывает при наличии ?sso= в URL.
    Обменивает одноразовый токен на access_token и refresh_token cookies.
    Токен удаляется из Redis сразу после использования.
    """
    raw = await redis_client.get(f"sso:{data.sso_token}")
    if not raw:
        raise HTTPException(status_code=401, detail="Invalid or expired SSO token")

    await redis_client.delete(f"sso:{data.sso_token}")

    user_id = int(raw.decode() if isinstance(raw, bytes) else raw)
    user = await UserDAO(session).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    access_token = AuthService._create_access_token(user)
    refresh_token_value = AuthService._create_refresh_token(user)
    _set_auth_cookies(response, access_token, refresh_token_value)

    return {"ok": True}
