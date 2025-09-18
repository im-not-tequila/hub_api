from fastapi import APIRouter, Depends, Query
from typing import List

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user
from app.schemas import UserResponse
from app.dao.mysql import StudentDAO, TutorDAO
from app.dao.postgres import UserInfoDAO
from app.db.session import get_mysql_session, get_postgres_session
from .schemas import TutorWithPosition


router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.
    """

    if current_user.platonus_id:
        async with get_mysql_session() as mysql_session:
            if current_user.is_student:
                platonus_user = await StudentDAO(mysql_session).get_one_or_none(StudentID=current_user.platonus_id)
            else:
                platonus_user = await TutorDAO(mysql_session).get_one_or_none(TutorID=current_user.platonus_id)

            firstname = platonus_user.firstname
            lastname = platonus_user.lastname
            patronymic = platonus_user.patronymic
    else:
        async with get_postgres_session() as postgres_session:
            user_info = await UserInfoDAO(postgres_session).get_one_or_none(user_id=current_user.id)
            firstname = user_info.firstname
            lastname = user_info.lastname
            patronymic = user_info.patronymic

    result_user = UserResponse(
        id=current_user.id,
        firstname=firstname,
        lastname=lastname,
        patronymic=patronymic,
    )

    return result_user


@router.get("/all_tutors_with_position", response_model=List[TutorWithPosition])
async def get_all_tutors_with_position(
    lang: str = Query('ru', description="Язык: ru, kz, en"),
    current_user: UserModel = Depends(get_current_user)
):
    async with get_mysql_session() as mysql_session:
        all_tutors_and_position = await TutorDAO(mysql_session).get_tutors_and_position()

        # Определяем поле name в зависимости от языка
        name_field = {
            'ru': 'nameru',
            'kz': 'namekz',
            'en': 'nameen'
        }.get(lang, 'nameru')

        # Формируем финальный список для ответа
        response = [
            {
                "tutor_id": item["TutorID"],
                "lastname": item["lastname"],
                "firstname": item["firstname"],
                "patronymic": item["patronymic"],
                "position_name": item[name_field]
            }
            for item in all_tutors_and_position
        ]

        return response
