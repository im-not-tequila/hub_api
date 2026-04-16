from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.mysql import TutorDAO, StudentDAO
from app.dao.postgres import UserDAO, RoleDao

from app.models.postgres import (
    User as UserModel,
    Role as RoleModel,
    UserRole as UserRoleModel
)
from app.models.mysql.nitro import (
    Student as StudentModel,
    Tutor as TutorModel,
    StructuralSubdivision as StructuralSubdivisionModel,
    TutorPositions as TutorPositionsModel
)


class MigrateUserMysqlToPostgres:
    def __init__(self, session_nitro: AsyncSession, session_postgres: AsyncSession):
        self.session_nitro = session_nitro
        self.session_postgres = session_postgres

    @staticmethod
    def _compute_tutor_role_ids(
        subdivision_position_rows: list[tuple],
        *,
        has_pps: bool,
    ) -> list[int]:
        """Роли сотрудника (tutor) по строкам join подразделение/должность; студентов не касается."""
        role_ids = [2, 11]  # Сотрудник университета, Физическое лицо

        for subdivision, _position in subdivision_position_rows:
            if subdivision:
                if subdivision.subdivision_type == 0:
                    role_ids.append(6)  # Проректор
                elif subdivision.subdivision_type == 2:
                    role_ids.append(7)  # Декан факультета
                elif subdivision.subdivision_type == 3:
                    role_ids.append(8)  # Заведующий кафедрой
                elif subdivision.id == 2:
                    role_ids.append(9)  # Отдел сопровождения развития персонала
                elif subdivision.id == 103:
                    role_ids.append(13)  # Ректор
                else:
                    role_ids.append(14)  # Руководитель структурных подразделений

        if has_pps:
            role_ids.append(10)  # Преподаватель

        seen: set[int] = set()
        ordered: list[int] = []
        for r in role_ids:
            if r not in seen:
                seen.add(r)
                ordered.append(r)
        return ordered

    async def _get_tutor_roles(self, tutor: TutorModel) -> list[RoleModel]:
        tutor_dao = TutorDAO(self.session_nitro)
        tutor_and_position = await tutor_dao.join_structural_subdivision_and_tutor_positions(
            filters={TutorModel.TutorID: tutor.TutorID},
            fields=[
                TutorModel.TutorID,
                StructuralSubdivisionModel.subdivision_type,
                StructuralSubdivisionModel.id,
                TutorPositionsModel.ID,
            ],
        )
        rows = [(sub, pos) for (_t, sub, pos) in tutor_and_position]
        pps_ids = await tutor_dao.get_tutor_ids_having_pps([tutor.TutorID])
        role_ids = self._compute_tutor_role_ids(rows, has_pps=tutor.TutorID in pps_ids)
        return await RoleDao(self.session_postgres).get_roles_by_ids(role_ids=role_ids)

    async def _get_student_roles(self, student: StudentModel) -> list[RoleModel]:
        role_ids = [1, 11]  # Обучающийся университета, Физическое лицо

        if student.isStudent == 3:
            role_ids.append(5)
        else:
            data = await StudentDAO(self.session_nitro).get_student_with_relations(student_id=student.StudentID)

            if data.get('studyform'):
                degree_id = int(data.get('studyform').DegreeID)

                if degree_id in [2, 3]:
                    role_ids.append(3)  # Магистрант

                if degree_id == 6:
                    role_ids.append(4)  # Научно-педагогическая форма обучения PhD

        roles = await RoleDao(self.session_postgres).get_roles_by_ids(role_ids=role_ids)

        return roles

    async def migrate_by_tutor_id(self, tutor_id: int, bin_number: str = None) -> UserModel | None:
        user = await UserDAO(self.session_postgres).get_one_or_none(
            filters={
                UserModel.platonus_id: tutor_id,
                UserModel.is_student: False
            }
        )

        if user and bin_number:
            await UserDAO(self.session_postgres).update(
                filters={UserModel.id: user.id},
                values={UserModel.bin_number: bin_number,}
            )

            await UserDAO(self.session_postgres).add_roles(
                user_id=user.id,
                role_ids=[12] # Юридическое лицо
            )

        tutor: TutorModel = await TutorDAO(self.session_nitro).get_one_or_none(
            filters={
                TutorModel.TutorID: tutor_id,
                TutorModel.has_access: 1,
                TutorModel.deleted: 0
            },
            fields=[TutorModel.TutorID]
        )

        if tutor:
            roles = await self._get_tutor_roles(tutor)
            user_roles = [UserRoleModel(role_id=role.id) for role in roles]

            if user is None:
                user = await UserDAO(self.session_postgres).add(
                    platonus_id=tutor.TutorID,
                    is_student=False,
                    user_roles=user_roles
                )

        if user:
            return user

        return None

    async def migrate_tutors_by_ids(self, tutor_ids: list[int]) -> dict[int, int]:
        """
        Пакетно создаёт в Postgres пользователей-сотрудников (is_student=False) для TutorID из Nitro.
        Студентов и migrate_by_student_id не использует. Передавайте только TutorID, для которых ещё нет
        записи user с тем же platonus_id и is_student=False, иначе возможны дубликаты.
        """
        if not tutor_ids:
            return {}

        unique = list(dict.fromkeys(tutor_ids))
        stmt = select(TutorModel.TutorID).where(
            TutorModel.TutorID.in_(unique),
            TutorModel.has_access == 1,
            TutorModel.deleted == 0,
        )
        res = await self.session_nitro.execute(stmt)
        eligible = [int(r[0]) for r in res.all()]
        if not eligible:
            return {}

        tutor_dao = TutorDAO(self.session_nitro)
        join_rows = await tutor_dao.join_structural_subdivision_and_tutor_positions(
            filters={TutorModel.TutorID: eligible},
            fields=[
                TutorModel.TutorID,
                StructuralSubdivisionModel.subdivision_type,
                StructuralSubdivisionModel.id,
                TutorPositionsModel.ID,
            ],
        )
        by_tutor: dict[int, list[tuple]] = defaultdict(list)
        for tutor, subdivision, position in join_rows:
            by_tutor[int(tutor.TutorID)].append((subdivision, position))

        pps_ids = await tutor_dao.get_tutor_ids_having_pps(eligible)

        per_tutor_role_ids: dict[int, list[int]] = {}
        for tid in eligible:
            rows = by_tutor.get(tid, [])
            per_tutor_role_ids[tid] = self._compute_tutor_role_ids(
                rows,
                has_pps=tid in pps_ids,
            )

        new_users: list[UserModel] = []
        for tid in eligible:
            rids = per_tutor_role_ids[tid]
            user_roles = [UserRoleModel(role_id=rid) for rid in rids]
            new_users.append(
                UserModel(
                    platonus_id=tid,
                    is_student=False,
                    user_roles=user_roles,
                )
            )

        self.session_postgres.add_all(new_users)
        await self.session_postgres.commit()
        for u in new_users:
            await self.session_postgres.refresh(u)

        return {int(u.platonus_id): int(u.id) for u in new_users}

    async def migrate_by_student_id(self, student_id: int) -> UserModel | None:
        user = await UserDAO(self.session_postgres).get_one_or_none(
            filters={
                UserModel.platonus_id: student_id,
                UserModel.is_student: True
            }
        )

        if user:
            return user

        student = await StudentDAO(self.session_nitro).get_one_or_none(
            filters={
                StudentModel.StudentID: student_id
            },
            fields=[StudentModel.StudentID, StudentModel.isStudent]
        )

        if student:
            roles = await self._get_student_roles(student)
            user_roles = [UserRoleModel(role_id=role.id) for role in roles]

            return await UserDAO(self.session_postgres).add(
                platonus_id=student.StudentID,
                is_student=True,
                user_roles=user_roles
            )

        return None
