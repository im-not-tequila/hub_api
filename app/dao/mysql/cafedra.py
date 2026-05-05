from app.dao.base import MySQLDao
from app.models.mysql.nitro import Cafedra


class CafedraDAO(MySQLDao):
    def __init__(self, session):
        super().__init__(session, Cafedra)
