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
from app.schemas import UserResponse, StructuralSubdivisionResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import ViceResponse


class UserService:
    def __init__(self, session_nitro: AsyncSession, session_postgres: AsyncSession, session_perco: AsyncSession):
        self.session_nitro = session_nitro
        self.session_postgres = session_postgres
        self.session_perco = session_perco

    async def user_data(self, current_user: UserModel) -> UserResponse:
        structural_subdivision = StructuralSubdivisionResponse(
            id=None,
            name_ru='',
            name_kz=''
        )

        post = ''
        is_dean = False

        if current_user.platonus_id:
            if current_user.is_student:
                platonus_user = await StudentDAO(self.session_nitro).get_one_or_none(
                    fields=[StudentModel.firstname, StudentModel.lastname, StudentModel.patronymic],
                    filters={
                        StudentModel.StudentID: current_user.platonus_id
                    }
                )

                structural_subdivision.name_ru = 'Студент'
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
                        StructuralSubdivisionModel.nameru,
                        StructuralSubdivisionModel.namekz,
                        StructuralSubdivisionModel.nameen,
                        StructuralSubdivisionModel.dean,
                        TutorPositions.NameRU,
                        TutorPositions.NameKZ,
                        TutorPositions.NameEN
                    ]
                )

                for _tutor, subdivision, position in rows:
                    structural_subdivision.id = subdivision.id
                    structural_subdivision.name_ru = subdivision.nameru
                    structural_subdivision.name_kz = subdivision.namekz

                    post = position.NameRU if position else ''

                    if subdivision.dean == current_user.platonus_id:
                        is_dean = True

                if structural_subdivision.name_ru == '':
                    structural_subdivision.name_ru = 'Сотрудник университета'

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

            structural_subdivision.name_ru = 'Гость'

        result_user = UserResponse(
            id=current_user.id,
            firstname=firstname,
            lastname=lastname,
            patronymic=patronymic,
            structural_subdivision=structural_subdivision,
            post=post,
            is_dean=is_dean
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

    async def vices(self, structural_subdivision_id: int):
        data = await TutorDAO(
            self.session_nitro,
            self.session_perco
        ).join_structural_subdivision_and_tutor_positions(
            fields=[
                TutorModel.TutorID,
                TutorModel.firstname,
                TutorModel.lastname,
                TutorModel.patronymic,
                StructuralSubdivisionModel.id,
                TutorPositions.NameRU,
                TutorPositions.NameKZ
            ],
            filters={
                StructuralSubdivisionModel.id: structural_subdivision_id,
            }
        )

        response_list = []

        for row in data:
            tutor, subdivision, position = row

            f_initial = f"{tutor.firstname[0]}." if tutor.firstname else ""
            p_initial = f"{tutor.patronymic[0]}." if tutor.patronymic else ""

            short_fio = f"{tutor.lastname} {f_initial}{p_initial}".strip()

            dto = ViceResponse(
                platonus_id=tutor.TutorID,
                lastname=tutor.lastname,
                firstname=tutor.firstname,
                patronymic=tutor.patronymic,
                shortname=short_fio
            )

            response_list.append(dto)

        return response_list


