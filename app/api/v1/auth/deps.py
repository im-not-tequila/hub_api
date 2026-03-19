from fastapi import Request, HTTPException, WebSocket, status, Depends
from jose import jwt, JWTError

from app.core.settings import get_settings
from app.db.session import get_postgres_session
from app.db.postgres_connection import async_session_postgres
from app.dao.postgres import UserDAO
from app.models.postgres.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

settings = get_settings()


def _extract_user_id_from_cookies(request: HTTPConnection) -> int:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return int(user_id)


async def get_current_user(
        request: HTTPConnection,
        session_postgres: AsyncSession = Depends(get_postgres_session)
) -> User:
    """
    Достает текущего пользователя из access-токена в cookie.
    Для обычных HTTP-запросов (сессия закрывается после ответа).
    """
    user_id = _extract_user_id_from_cookies(request)

    user_dao = UserDAO(session_postgres)
    user = await user_dao.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_user_ws(websocket: WebSocket) -> User:
    """
    Достает текущего пользователя для WebSocket-соединений.
    Открывает и сразу закрывает сессию, чтобы не держать соединение из пула.
    """
    user_id = _extract_user_id_from_cookies(websocket)

    async with async_session_postgres() as session:
        user_dao = UserDAO(session)
        user = await user_dao.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
