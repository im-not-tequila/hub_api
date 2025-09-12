from fastapi import HTTPException
from datetime import datetime, timedelta, UTC
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError

from app.core.settings import get_settings
from app.dao.mysql import StudentDAO, TutorDAO
from app.dao.postgres import UserDAO, UserInfoDAO
from app.models.postgres import User as UserModel
from app.db.session import get_postgres_session, get_mysql_session
from app.schemas_internal import UserEcpInfo, Tokens


settings = get_settings()


class AuthService:
    @staticmethod
    async def authenticate_by_ecp(user_ecp_info: UserEcpInfo) -> UserModel:
        async with get_postgres_session() as postgres_session:
            async with get_mysql_session() as mysql_session:
                tutor_dao = TutorDAO(mysql_session)
                user_dao = UserDAO(postgres_session)
                tutor = await tutor_dao.get_by_iin(user_ecp_info.iin_number)
                user = None

                if tutor:
                    user = await user_dao.get_one_or_none(platonus_id=tutor.TutorID)

                    if user is None:
                        user = await user_dao.add(platonus_id=tutor.TutorID, is_student=False)

                if user:
                    return user

                student_dao = StudentDAO(mysql_session)
                student = await student_dao.get_by_iin(user_ecp_info.iin_number, is_student=[1, 3])

                if student:
                    user = await user_dao.get_one_or_none(platonus_id=student.StudentID)

                    if user is None:
                        user = await user_dao.add(platonus_id=student.StudentID, is_student=True)

                if user is None:
                    user_info_dao = UserInfoDAO(postgres_session)
                    user = await user_dao.add(platonus_id=None, is_student=False)
                    await user_info_dao.add(
                        user_id=user.id,
                        lastname=user_ecp_info.lastname,
                        firstname=user_ecp_info.firstname,
                        patronymic=user_ecp_info.patronymic,
                        iin_number=user_ecp_info.iin_number
                    )

                return user

    @staticmethod
    async def authenticate_by_platonus(login: str, password: str) -> UserModel:
        async with get_postgres_session() as postgres_session:
            async with get_mysql_session() as mysql_session:
                tutor_dao = TutorDAO(mysql_session)
                user_dao = UserDAO(postgres_session)
                tutor = await tutor_dao.get_by_platonus_credentials(login, password)
                user = None

                if tutor:
                    user = await user_dao.get_one_or_none(platonus_id=tutor.TutorID)

                    if user is None:
                        user = await user_dao.add(platonus_id=tutor.TutorID, is_student=False)

                if user:
                    return user

                student_dao = StudentDAO(mysql_session)
                student = await student_dao.get_by_platonus_credentials(login, password)

                if student:
                    user = await user_dao.get_one_or_none(platonus_id=student.StudentID)

                    if user is None:
                        user = await user_dao.add(platonus_id=student.StudentID, is_student=True)

                return user

    @staticmethod
    def _create_access_token(user: UserModel):
        now = datetime.now(UTC)

        access_payload = {
            "sub": str(user.id),
            "username": user.id,
            "iat": now,
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        }

        return jwt.encode(access_payload, settings.SECRET_KEY)

    @staticmethod
    def _create_refresh_token(user: UserModel):
        now = datetime.now(UTC)

        refresh_payload = {
            "sub": str(user.id),
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        }

        return jwt.encode(refresh_payload, settings.SECRET_KEY)

    @classmethod
    def create_tokens(cls, user: UserModel) -> Tokens:
        """
        Создание пары токенов: access + refresh.
        """

        access_token = cls._create_access_token(user)
        refresh_token = cls._create_refresh_token(user)

        tokens = Tokens(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
        )

        return tokens

    @classmethod
    async def refresh_access_token(cls, refresh_token: str):
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token missing")

        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = int(payload.get("sub"))
        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh token expired")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        async with get_postgres_session() as postgres_session:
            user = await UserDAO(postgres_session).get_by_id(user_id)
            new_access_token = cls._create_access_token(user)

            return new_access_token
