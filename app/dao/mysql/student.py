import hashlib

from app.dao.base import MySQLDao
from app.models.mysql.student import Student
from sqlalchemy import select


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
