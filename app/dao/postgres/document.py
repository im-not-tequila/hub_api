from sqlalchemy import select, or_
from sqlalchemy.orm import contains_eager, joinedload
from typing import List

from app.dao.base import PostgresDao

from app.models.postgres import (
    Document,
    DocumentTypeGroup,
    RoleDocumentTypeGroup,
    Role,
    UserRole,
    DocumentType,
    Executor,
    ExecutorStatus,
    Approver
)


class DocumentDAO(PostgresDao):
    def __init__(self, session):
        super().__init__(session, Document)

    async def get_all_types_and_categories(self, user_id: int) -> list[DocumentTypeGroup]:
        """
        Возвращает все активные категории с их активными типами документов,
        доступные конкретному пользователю.
        """
        query = (
            select(DocumentTypeGroup)
            .join(DocumentTypeGroup.roles)  # -> RoleDocumentTypeGroup
            .join(RoleDocumentTypeGroup.role)  # -> Role
            .join(Role.user_roles)  # -> UserRole
            .join(DocumentTypeGroup.document_types)  # -> DocumentType
            .where(
                DocumentTypeGroup.is_active == True,
                Role.is_active == True,
                UserRole.user_id == user_id,
                DocumentType.is_active == True  # фильтр по документам
            )
            .options(contains_eager(DocumentTypeGroup.document_types))  # чтобы doc_types подгружались сразу
            .order_by(DocumentTypeGroup.id)
        )

        result = await self.session.execute(query)
        groups: list[DocumentTypeGroup] = list(result.scalars().unique().all())
        return groups

    async def incoming(self, user_id: int) -> List[Document]:
        approver_exists = (
            select(Approver.id)
            .where(Approver.document_id == Document.id, Approver.approver_id == user_id)
            .exists()
        )

        query = (
            select(Document)
            .where(
                or_(
                    Document.recipient_id == user_id,
                    approver_exists
                )
            )
            .order_by(Document.created_at.desc())
        )

        result = await self.session.execute(query)
        documents: List[Document] = list(result.scalars().unique().all())

        return documents


    async def outgoing(self, user_id: int) -> List[Document]:
        query = (
            select(Document)
            .where(Document.author_id == user_id)
            .order_by(Document.created_at.desc())
        )

        result = await self.session.execute(query)
        documents: List[Document] = list(result.scalars().unique().all())

        return documents

    async def pending_execution(self, user_id: int) -> List[Document]:
        query = (
            select(Document)
            .join(Executor, Executor.document_id == Document.id)
            .where(Executor.executor_id == user_id)
            .where(Executor.status == ExecutorStatus.PENDING_EXECUTION)  # только в ожидании
            .options(joinedload(Document.document_type))  # подтягиваем тип документа
            .options(joinedload(Document.author_user))    # подтягиваем автора
            .order_by(Document.created_at.desc())
        )

        result = await self.session.execute(query)
        documents: List[Document] = list(result.scalars().unique().all())

        return documents

    async def executed(self, user_id: int) -> List[Document]:
        query = (
            select(Document)
            .join(Executor, Executor.document_id == Document.id)
            .where(Executor.executor_id == user_id)
            .where(Executor.status == ExecutorStatus.COMPLETED)
            .options(joinedload(Document.document_type))  # подтягиваем тип документа
            .options(joinedload(Document.author_user))    # подтягиваем автора
            .order_by(Document.created_at.desc())
        )

        result = await self.session.execute(query)
        documents: List[Document] = list(result.scalars().unique().all())

        return documents
