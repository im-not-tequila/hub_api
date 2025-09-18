from app.dao.base import PostgresDao
from app.models.postgres import Approver


class ApproverDAO(PostgresDao):
    def __init__(self, session):
        super().__init__(session, Approver)
