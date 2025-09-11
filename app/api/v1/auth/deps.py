from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.session import get_postgres_session
from app.models.postgres.user import User
from app.dao.postgres import UserDAO


settings = get_settings()

# Указываем эндпоинт для получения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    Достает текущего пользователя из access-токена.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    async with get_postgres_session() as session:
        user_dao = UserDAO(session)
        user = await user_dao.get_by_id(int(user_id))

        if user is None:
            raise credentials_exception

        return user
