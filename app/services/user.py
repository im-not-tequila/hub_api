import datetime
from fastapi import HTTPException

from app.dao.mysql import TutorDAO, PersontabelDAO, StudentDAO
from app.dao.postgres import UserInfoDAO
from app.models.postgres import (
    User as UserModel
)
from app.models.mysql.nitro import (
    Tutor as TutorModel,
    Student as StudentModel,
    StructuralSubdivision as StructuralSubdivisionModel, TutorPositions
)
from app.schemas import UserResponse
from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    def __init__(self, session_nitro: AsyncSession, session_postgres: AsyncSession, session_perco: AsyncSession):
        self.session_nitro = session_nitro
        self.session_postgres = session_postgres
        self.session_perco = session_perco

    async def user_data(self, current_user: UserModel) -> UserResponse:
        structural_subdivision = ''
        post = ''
        subdivision_id = None

        if current_user.platonus_id:
            if current_user.is_student:
                platonus_user = await StudentDAO(self.session_nitro).get_one_or_none(
                    fields=[StudentModel.firstname, StudentModel.lastname, StudentModel.patronymic],
                    filters={
                        StudentModel.StudentID: current_user.platonus_id
                    }
                )

                structural_subdivision = 'Студент'
            else:
                platonus_user = await TutorDAO(self.session_nitro).get_one_or_none(
                    fields=[TutorModel.firstname, TutorModel.lastname, TutorModel.patronymic],
                    filters={
                        TutorModel.TutorID: current_user.platonus_id
                    }
                )

                rows = await TutorDAO(self.session_nitro).join_structural_subdivision_and_tutor_positions(
                    filters={
                        StructuralSubdivisionModel.subdivision_type: [0, 1, 2, 3],
                        TutorModel.TutorID: current_user.platonus_id,
                    },
                    fields=[
                        TutorModel.TutorID,
                        StructuralSubdivisionModel.id,
                        StructuralSubdivisionModel.nameru,
                        StructuralSubdivisionModel.namekz,
                        StructuralSubdivisionModel.nameen,
                        TutorPositions.NameRU,
                        TutorPositions.NameKZ,
                        TutorPositions.NameEN
                    ]
                )

                for _tutor, subdivision, position in rows:
                    subdivision_id = subdivision.id
                    structural_subdivision = subdivision.nameru
                    post = position.NameRU if position else ''

                if structural_subdivision == '':
                    structural_subdivision = 'Сотрудник университета'

            firstname = platonus_user.firstname
            lastname = platonus_user.lastname
            patronymic = platonus_user.patronymic
        else:
            user_info = await UserInfoDAO(self.session_postgres).get_one_or_none(
                filters={
                    UserModel.id: current_user.id
                }
            )
            firstname = user_info.firstname
            lastname = user_info.lastname
            patronymic = user_info.patronymic

            structural_subdivision = 'Гость'

        result_user = UserResponse(
            id=current_user.id,
            firstname=firstname,
            lastname=lastname,
            patronymic=patronymic,
            structural_subdivision=structural_subdivision,
            subdivision_id=subdivision_id,
            post=post
        )

        return result_user

    async def visit_history_barrier(self, user: UserModel, target_date: datetime.date):
        if user.is_student:
            raise HTTPException(status_code=403, detail="Access denied for students")

        actions = await TutorDAO(self.session_nitro, self.session_perco).get_tutor_actions_barrier_by_date(user.platonus_id, target_date)

        return actions

    async def visit_history_working_hours(self, user: UserModel, start_date: datetime.date, finish_date: datetime.date):
        if user.is_student:
            raise HTTPException(status_code=403, detail="Access denied for students")

        dao = PersontabelDAO(self.session_perco)
        working_hours = await dao.get_tutor_working_hours(
            start_date=start_date,
            finish_date=finish_date,
            person_id=user.platonus_id
        )

        return working_hours



