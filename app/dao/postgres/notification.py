from app.dao.base import PostgresDao
from app.models.postgres import Notification


class NotificationDAO(PostgresDao):
    def __init__(self, session):
        super().__init__(session, Notification)
