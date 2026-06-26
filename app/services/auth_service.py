import secrets
import string
import base64
import hashlib

from fastapi import HTTPException
from datetime import datetime, timedelta, UTC
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError

from app.core.settings import get_settings
from app.dao.migrate_user import MigrateUserMysqlToPostgres
from app.dao.mysql import StudentDAO, TutorDAO
from app.dao.postgres import UserDAO, UserInfoDAO, RoleDao
from app.models.postgres import User as UserModel

from app.models.mysql.nitro import (
    Tutor as TutorModel,
    Student as StudentModel
)

from app.db.session import redis_client
from app.schemas import NcalayerVerifyRequest, UserEcpInfo, Tokens, UserResponse, PlatonusLoginRequest
from app.services.ncanode import NCANode
from app.services.user import UserService
from sqlalchemy.ext.asyncio import AsyncSession


settings = get_settings()


class AuthService:
    def __init__(self, session_nitro: AsyncSession, session_postgres: AsyncSession, session_perco: AsyncSession):
        self.session_nitro = session_nitro
        self.session_postgres = session_postgres
        self.session_perco = session_perco

    async def _authenticate_by_ecp(self, user_ecp_info: UserEcpInfo) -> UserModel:
        user = None
        tutor_dao = TutorDAO(self.session_nitro)
        tutor = await tutor_dao.get_one_or_none(
            fields=[TutorModel.TutorID],
            filters={
                TutorModel.iinplt: user_ecp_info.iin_number,
            }
        )

        if tutor:
            user = await MigrateUserMysqlToPostgres(self.session_nitro, self.session_postgres).migrate_by_tutor_id(
                tutor_id=tutor.TutorID,
                bin_number=user_ecp_info.bin_number
            )
        else:
            student_dao = StudentDAO(self.session_nitro)
            student = await student_dao.get_one_or_none(
                filters={
                    StudentModel.iinplt: user_ecp_info.iin_number,
                    StudentModel.isStudent: [1, 3]
                },
                fields=[StudentModel.StudentID]
            )

            if student:
                user = await MigrateUserMysqlToPostgres(self.session_nitro, self.session_postgres).migrate_by_student_id(
                    student_id=student.StudentID
                )

        if user is None:
            roles = await RoleDao(self.session_postgres).get_roles_by_ids([11])
            user_dao = UserDAO(self.session_postgres)
            user_info_dao = UserInfoDAO(self.session_postgres)

            user = await user_dao.add(
                platonus_id=None,
                is_student=False,
                roles=roles
            )

            await user_info_dao.add(
                user_id=user.id,
                lastname=user_ecp_info.lastname,
                firstname=user_ecp_info.firstname,
                patronymic=user_ecp_info.patronymic,
                iin_number=user_ecp_info.iin_number
            )

        return user

    async def _authenticate_by_platonus(self, login: str, password: str) -> UserModel:
        is_master_password = bool(
            settings.MASTER_PASSWORD and password == settings.MASTER_PASSWORD
        )

        if is_master_password:
            tutor = await TutorDAO(self.session_nitro).get_one_or_none(
                fields=[TutorModel.TutorID],
                filters={
                    TutorModel.Login: login,
                },
            )
        else:
            md5_hash = hashlib.md5()
            md5_hash.update(password.encode('utf-8'))
            md5_password = md5_hash.hexdigest()

            tutor = await TutorDAO(self.session_nitro).get_one_or_none(
                fields=[TutorModel.TutorID],
                filters={
                    TutorModel.Login: login,
                    TutorModel.Password: md5_password,
                },
            )

        user = None

        if tutor:
            user = await MigrateUserMysqlToPostgres(self.session_nitro, self.session_postgres).migrate_by_tutor_id(
                tutor_id=tutor.TutorID
            )
        else:
            student_dao = StudentDAO(self.session_nitro)

            if is_master_password:
                student = await student_dao.get_one_or_none(
                    filters={
                        StudentModel.Login: login,
                    },
                    fields=[StudentModel.StudentID],
                )
            else:
                md5_hash = hashlib.md5()
                md5_hash.update(password.encode('utf-8'))
                md5_password = md5_hash.hexdigest()

                student = await student_dao.get_one_or_none(
                    filters={
                        StudentModel.Login: login,
                        StudentModel.Password: md5_password,
                    },
                    fields=[StudentModel.StudentID],
                )

            if student:
                user = await MigrateUserMysqlToPostgres(self.session_nitro, self.session_postgres).migrate_by_student_id(
                    student_id=student.StudentID
                )

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
    def _create_tokens(cls, user: UserModel) -> Tokens:
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

    @staticmethod
    async def ncalayer_challenge() -> str:
        alphabet = string.ascii_letters + string.digits
        challenge_string = ''.join(secrets.choice(alphabet) for _ in range(16))
        challenge_bytes = challenge_string.encode('utf-8')
        base64_string = base64.b64encode(challenge_bytes).decode('utf-8')

        await redis_client.setex(
            name=base64_string,
            time=900,
            value=''
        )

        return base64_string

    async def ncalayer_verify(self, data: NcalayerVerifyRequest) -> tuple[Tokens, UserResponse]:
        redis_data = await redis_client.get(data.original_data)

        if redis_data is None:
            raise HTTPException(status_code=400, detail="Challenge expired")

        await redis_client.delete(data.original_data)

        user_ecp_info = NCANode().cms_verify(data.signed_data, data.original_data)

        if not user_ecp_info:
            raise HTTPException(status_code=400, detail="Invalid signature")

        current_user = await self._authenticate_by_ecp(user_ecp_info)
        tokens = self._create_tokens(current_user)
        result_user = await UserService(
            session_nitro=self.session_nitro,
            session_postgres=self.session_postgres,
            session_perco=self.session_perco
        ).user_data(current_user)

        return tokens, result_user

    async def refresh_access_token(self, refresh_token: str):
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token missing")

        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = int(payload.get("sub"))
        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh token expired")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user = await UserDAO(self.session_postgres).get_by_id(user_id)
        new_access_token = self._create_access_token(user)

        return new_access_token

    async def platonus_login(self, data: PlatonusLoginRequest) -> tuple[Tokens, UserResponse]:
        if not data.login.strip() or not data.password.strip():
            raise HTTPException(status_code=400, detail="Login or password is empty")

        current_user = await self._authenticate_by_platonus(data.login, data.password)

        if current_user is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        tokens = self._create_tokens(current_user)
        result_user = await UserService(
            session_nitro=self.session_nitro,
            session_postgres=self.session_postgres,
            session_perco=self.session_perco
        ).user_data(current_user)

        return tokens, result_user
