import datetime
from fastapi import HTTPException

from app.db.session import get_mysql_session, get_postgres_session
from app.dao.mysql import TutorDAO, PersontabelDAO, StudentDAO
from app.dao.postgres import UserInfoDAO
from app.models.postgres import (
    User as UserModel
)
from app.models.mysql.nitro import (
    Tutor as TutorModel,
    Student as StudentModel,
    StructuralSubdivision as StructuralSubdivisionModel
)
from app.schemas import UserResponse


class UserService:
    async def user_data(self, current_user: UserModel) -> UserResponse:
        if current_user.platonus_id:
            async with get_mysql_session() as mysql_session:
                if current_user.is_student:
                    platonus_user = await StudentDAO(mysql_session).get_one_or_none(
                        fields=[StudentModel.firstname, StudentModel.lastname, StudentModel.patronymic],
                        StudentID=current_user.platonus_id
                    )

                    structural_subdivision = 'Студент'
                else:
                    platonus_user = await TutorDAO(mysql_session).get_one_or_none(
                        fields=[TutorModel.firstname, TutorModel.lastname, TutorModel.patronymic],
                        TutorID=current_user.platonus_id
                    )

                    rows = await TutorDAO(mysql_session).get_tutors_and_position(
                        filters={
                            StructuralSubdivisionModel.subdivision_type: [0, 1, 2, 3],
                            TutorModel.TutorID: current_user.platonus_id,
                        }
                    )

                    if rows:
                        structural_subdivision = rows[0][1].nameru  # второй элемент первого кортежа
                        print('00000000000000000000000000000')
                        print(rows[0][1])
                    else:
                        structural_subdivision = 'Сотрудник университета'

                firstname = platonus_user.firstname
                lastname = platonus_user.lastname
                patronymic = platonus_user.patronymic
        else:
            async with get_postgres_session() as postgres_session:
                user_info = await UserInfoDAO(postgres_session).get_one_or_none(user_id=current_user.id)
                firstname = user_info.firstname
                lastname = user_info.lastname
                patronymic = user_info.patronymic

                structural_subdivision = 'Гость'

        result_user = UserResponse(
            id=current_user.id,
            firstname=firstname,
            lastname=lastname,
            patronymic=patronymic,
            structural_subdivision=structural_subdivision
        )

        return result_user

    async def visit_history_barrier(self, user: UserModel, target_date: datetime.date):
        if user.is_student:
            raise HTTPException(status_code=403, detail="Access denied for students")

        async with get_mysql_session('perco') as mysql_session_perco:
            async with get_mysql_session() as mysql_session_nitro:
                actions = await TutorDAO(mysql_session_nitro, mysql_session_perco).get_tutor_actions_barrier_by_date(user.platonus_id, target_date)

            return actions

    async def visit_history_working_hours(self, user: UserModel, start_date: datetime.date, finish_date: datetime.date):
        if user.is_student:
            raise HTTPException(status_code=403, detail="Access denied for students")

        async with get_mysql_session(db_name="perco") as mysql_session:
            dao = PersontabelDAO(mysql_session)
            working_hours = await dao.get_tutor_working_hours(
                start_date=start_date,
                finish_date=finish_date,
                person_id=user.platonus_id
            )

            return working_hours



