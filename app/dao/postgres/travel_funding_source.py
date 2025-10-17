from app.dao.base import PostgresDao
from app.models.postgres import TravelFundingSource


class TravelFundingSourceDAO(PostgresDao):
    def __init__(self, session):
        super().__init__(session, TravelFundingSource)
