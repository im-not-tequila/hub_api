from app.dao.base import PostgresDao
from app.models.postgres import Document, DocumentType, DocumentTypeGroup


class DocumentDAO(PostgresDao):
    def __init__(self, session):
        super().__init__(session, Document)
