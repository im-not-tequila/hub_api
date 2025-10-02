import secrets
import string
import base64

from fastapi import HTTPException
from datetime import datetime, timedelta, UTC
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError

from app.core.settings import get_settings
from app.dao.migrate_user import MigrateUserMysqlToPostgres
from app.dao.mysql import StudentDAO, TutorDAO
from app.dao.postgres import UserDAO, UserInfoDAO, RoleDao
from app.models.postgres import User as UserModel
from app.db.session import get_postgres_session, get_mysql_session, redis_client
from app.schemas import NcalayerVerifyRequest, UserEcpInfo, Tokens, UserResponse, PlatonusLoginRequest
from app.services.ncanode import NCANode


settings = get_settings()


class AuthService:
    @staticmethod
    async def _authenticate_by_ecp(user_ecp_info: UserEcpInfo) -> UserModel:
        async with get_postgres_session() as postgres_session:
            async with get_mysql_session() as mysql_session:
                user = None
                tutor_dao = TutorDAO(mysql_session)
                tutor = await tutor_dao.get_by_iin(user_ecp_info.iin_number)

                if tutor:
                    user = await MigrateUserMysqlToPostgres(mysql_session, postgres_session).migrate_by_tutor_id(
                        tutor_id=tutor.TutorID,
                        bin_number=user_ecp_info.bin_number
                    )
                else:
                    student_dao = StudentDAO(mysql_session)
                    student = await student_dao.get_by_iin(user_ecp_info.iin_number, is_student=[1, 3])

                    if student:
                        user = await MigrateUserMysqlToPostgres(mysql_session, postgres_session).migrate_by_student_id(
                            student_id=student.StudentID
                        )

                if user is None:
                    roles = await RoleDao(postgres_session).get_roles_by_ids([11])
                    user_dao = UserDAO(postgres_session)
                    user_info_dao = UserInfoDAO(postgres_session)

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

    @staticmethod
    async def _authenticate_by_platonus(login: str, password: str) -> UserModel:
        async with get_postgres_session() as postgres_session:
            async with get_mysql_session() as mysql_session:
                tutor_dao = TutorDAO(mysql_session)
                user_dao = UserDAO(postgres_session)
                tutor = await tutor_dao.get_by_platonus_credentials(login, password)
                user = None

                if tutor:
                    user = await MigrateUserMysqlToPostgres(mysql_session, postgres_session).migrate_by_tutor_id(
                        tutor_id=tutor.TutorID
                    )
                else:
                    student_dao = StudentDAO(mysql_session)
                    student = await student_dao.get_by_platonus_credentials(login, password)

                    if student:
                        user = await MigrateUserMysqlToPostgres(mysql_session, postgres_session).migrate_by_student_id(
                            student_id=student.StudentID
                        )

                # if user is None:
                #     user = await user_dao.add(platonus_id=student.StudentID, is_student=True)

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

        user_model = await self._authenticate_by_ecp(user_ecp_info)
        tokens = self._create_tokens(user_model)

        firstname = user_ecp_info.firstname
        lastname = user_ecp_info.lastname
        patronymic = user_ecp_info.patronymic

        result_user = UserResponse(
            id=user_model.id,
            firstname=firstname,
            lastname=lastname,
            patronymic=patronymic,
        )

        return tokens, result_user

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

    async def platonus_login(self, data: PlatonusLoginRequest):
        if not data.login.strip() or not data.password.strip():
            raise HTTPException(status_code=400, detail="Login or password is empty")

        user_model = await self._authenticate_by_platonus(data.login, data.password)

        if user_model is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        tokens = self._create_tokens(user_model)

        async with get_mysql_session() as mysql_session:
            if user_model.is_student:
                platonus_user = await StudentDAO(mysql_session).get_one_or_none(StudentID=user_model.platonus_id)
            else:
                platonus_user = await TutorDAO(mysql_session).get_one_or_none(TutorID=user_model.platonus_id)

            firstname = platonus_user.firstname
            lastname = platonus_user.lastname
            patronymic = platonus_user.patronymic

        result_user = UserResponse(
            id=user_model.id,
            firstname=firstname,
            lastname=lastname,
            patronymic=patronymic,
        )

        return tokens, result_user
