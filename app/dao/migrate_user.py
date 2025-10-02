from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.mysql import TutorDAO, StudentDAO
from app.dao.postgres import UserDAO, RoleDao
from app.models.postgres import User, Role, UserRole
from app.models.mysql import Student, Tutor


class MigrateUserMysqlToPostgres:
    def __init__(self, mysql_session: AsyncSession, postgres_session: AsyncSession):
        self.mysql_session = mysql_session
        self.postgres_session = postgres_session

    async def _get_tutor_roles(self, tutor: Tutor) -> list[Role]:
        role_ids = [2, 11] # Сотрудник университета, Физическое лицо

        tutor_and_position = await TutorDAO(self.mysql_session).get_tutors_and_position(
            filters={
                Tutor.TutorID: tutor.TutorID
            }
        )

        for _, position in tutor_and_position:
            if position:
                if position.subdivision_type == 0:
                    role_ids.append(6) # Проректор
                elif position.subdivision_type == 2:
                    role_ids.append(7) # Декан факультета
                elif position.subdivision_type == 3:
                    role_ids.append(8) # Заведующий кафедрой
                elif position.id == 2:
                    role_ids.append(9) # Отдел сопровождения развития персонала
                elif position.id == 103:
                    role_ids.append(13) # Ректор

        tutor_and_position_pps = await TutorDAO(self.mysql_session).get_tutor_positions_pps(
            tutor_id=tutor.TutorID,
        )

        if len(tutor_and_position_pps) > 0:
            role_ids.append(10) # Преподаватель

        roles = await RoleDao(self.postgres_session).get_roles_by_ids(role_ids=role_ids)

        return roles

    async def _get_student_roles(self, student: Student) -> list[Role]:
        role_ids = [1, 11]  # Обучающийся университета, Физическое лицо

        if student.isStudent == 3:
            role_ids.append(5)
        else:
            data = await StudentDAO(self.mysql_session).get_student_with_relations(student_id=student.StudentID)

            if data.get('studyform'):
                degree_id = int(data.get('studyform').DegreeID)

                if degree_id in [2, 3]:
                    role_ids.append(3)  # Магистрант

                if degree_id == 6:
                    role_ids.append(4)  # Научно-педагогическая форма обучения PhD

        roles = await RoleDao(self.postgres_session).get_roles_by_ids(role_ids=role_ids)

        return roles

    async def migrate_by_tutor_id(self, tutor_id: int, bin_number: str = None) -> User | None:
        user = await UserDAO(self.postgres_session).get_one_or_none(platonus_id=tutor_id, is_student=False)

        if user and bin_number:
            await UserDAO(self.postgres_session).update(
                obj_id=user.id,
                bin_number=bin_number,
            )

            await UserDAO(self.postgres_session).add_roles(
                user_id=user.id,
                role_ids=[12] # Юридическое лицо
            )

        if user:
            return user

        tutor: Tutor = await TutorDAO(self.mysql_session).get_one_or_none(TutorID=tutor_id, has_access=1, deleted=0)

        if tutor:
            roles = await self._get_tutor_roles(tutor)
            user_roles = [UserRole(role_id=role.id) for role in roles]

            return await UserDAO(self.postgres_session).add(
                platonus_id=tutor.TutorID,
                is_student=False,
                user_roles=user_roles
            )

        return None

    async def migrate_by_student_id(self, student_id: int) -> User | None:
        user = await UserDAO(self.postgres_session).get_one_or_none(platonus_id=student_id, is_student=True)

        if user:
            return user

        student = await StudentDAO(self.mysql_session).get_one_or_none(StudentID=student_id)

        if student:
            roles = await self._get_student_roles(student)
            user_roles = [UserRole(role_id=role.id) for role in roles]

            return await UserDAO(self.postgres_session).add(
                platonus_id=student.StudentID,
                is_student=True,
                user_roles=user_roles
            )

        return None
