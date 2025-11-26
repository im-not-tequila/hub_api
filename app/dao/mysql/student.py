from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.dao.base import MySQLDao
from app.models.mysql.nitro import Student, Studyform, Group


class StudentDAO(MySQLDao):
    def __init__(self, session):
        super().__init__(session, Student)

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
