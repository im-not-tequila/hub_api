from fastapi import Request, WebSocket, HTTPException, status
from jose import jwt, JWTError

from app.core.settings import get_settings
from app.db.session import get_postgres_session
from app.dao.postgres import UserDAO
from app.models.postgres.user import User

settings = get_settings()

async def get_current_user(request: Request) -> User:
    """
    Достает текущего пользователя из access-токена в cookie.
    Работает и для обычных запросов, и для WebSocket.
    """

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

    async with get_postgres_session() as session:
        user_dao = UserDAO(session)
        user = await user_dao.get_by_id(int(user_id))

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

    return user
