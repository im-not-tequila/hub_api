import hashlib

from app.dao.base import MySQLDao
from app.models.mysql.tutor import Tutor
from sqlalchemy import select


class TutorDAO(MySQLDao):
    def __init__(self, session):
        super().__init__(session, Tutor)

    async def get_by_iin(self, iin: str) -> Tutor:
        stmt = select(Tutor).where(Tutor.iinplt == iin)
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_by_platonus_credentials(self, login: str, password: str):
        md5_hash = hashlib.md5()
        md5_hash.update(password.encode('utf-8'))
        md5_password = md5_hash.hexdigest()

        stmt = select(Tutor).where(Tutor.Login == login, Tutor.Password == md5_password)
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()
