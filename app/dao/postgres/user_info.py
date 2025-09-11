from app.dao.base import PostgresDao
from app.models.postgres import UserInfo


class UserInfoDAO(PostgresDao):
    def __init__(self, session):
        super().__init__(session, UserInfo)
