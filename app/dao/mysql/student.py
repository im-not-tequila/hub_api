import hashlib

from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.dao.base import MySQLDao
from app.models.mysql import Student, Studyform, Group


class StudentDAO(MySQLDao):
    def __init__(self, session):
        super().__init__(session, Student)

    async def get_by_iin(self, iin: str, is_student: list[int] | None = None) -> Student | None:
        stmt = select(Student).where(Student.iinplt == iin)

        if is_student:
            stmt = stmt.where(Student.isStudent.in_(is_student))

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_by_platonus_credentials(self, login: str, password: str):
        md5_hash = hashlib.md5()
        md5_hash.update(password.encode('utf-8'))
        md5_password = md5_hash.hexdigest()

        stmt = select(Student).where(Student.Login == login, Student.Password == md5_password)
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_student_with_relations(self, student_id: int):
        sf = aliased(Studyform)
        g = aliased(Group)

        query = (
            select(
                Student,
                sf,
                g
            )
            .outerjoin(sf, Student.StudyFormID == sf.Id)  # LEFT JOIN с studyforms
            .outerjoin(g, Student.groupID == g.groupID)  # LEFT JOIN с groups
            .where(Student.StudentID == student_id)  # фильтр по студенту
        )

        result = await self.session.execute(query)
        row = result.one_or_none()  # возвращаем None, если студент не найден

        if row:
            student, studyform, group = row
            return {
                "student": student,
                "studyform": studyform,
                "group": group
            }

        return None
