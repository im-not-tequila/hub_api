from app.dao.base import PostgresDao
from app.models.postgres import User


class UserDAO(PostgresDao):
    def __init__(self, session):
        super().__init__(session, User)
