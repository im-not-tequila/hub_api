from app.dao.base import MySQLDao
from app.models.mysql.nitro import StructuralSubdivision


class StructuralSubdivisionDAO(MySQLDao):
    def __init__(self, session):
        super().__init__(session, StructuralSubdivision)
