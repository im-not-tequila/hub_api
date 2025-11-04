from app.dao.base import PostgresDao
from app.models.postgres import SampleDocument


class SampleDocumentDAO(PostgresDao):
    def __init__(self, session):
        super().__init__(session, SampleDocument)
