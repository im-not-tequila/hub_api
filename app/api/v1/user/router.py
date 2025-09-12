from fastapi import APIRouter, Depends

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user
from app.schemas_internal import User
from app.dao.mysql import StudentDAO, TutorDAO
from app.dao.postgres import UserInfoDAO
from app.db.session import get_mysql_session, get_postgres_session


router = APIRouter()


@router.get("/me", response_model=User)
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

    result_user = User(
        id=current_user.id,
        firstname=firstname,
        lastname=lastname,
        patronymic=patronymic,
    )

    return result_user
