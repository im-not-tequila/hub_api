from sqlalchemy import update, select

# from datetime import datetime, UTC

from app.dao.base import PostgresDao
from app.models.postgres import Approver, ApproverStatus


class ApproverDAO(PostgresDao):
    def __init__(self, session):
        super().__init__(session, Approver)

    async def set_status(
            self,
            document_id: int,
            approver_id: int,
            status: ApproverStatus
    ) -> Approver | None:
        """
        Обновляет статус аппрувера.
        Если статус = SIGNED → ставим signed_at.
        """
        stmt = (
            update(Approver)
            .where(
                Approver.document_id == document_id,
                Approver.approver_id == approver_id
            )
            .values(
                status=status
            )
            .returning(Approver)
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.scalar_one_or_none()

    async def set_resolution(
            self,
            document_id: int,
            approver_id: int,
            resolution: str
    ) -> Approver | None:
        stmt = (
            update(Approver)
            .where(
                Approver.document_id == document_id,
                Approver.approver_id == approver_id
            )
            .values(
                resolution=resolution,
            )
            .returning(Approver)
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.scalar_one_or_none()

    async def add_if_not_exists(self, document_id: int, approver_id: int, is_recipient: bool = False) -> Approver | None:
        existing = await self.session.scalar(
            select(Approver)
            .where(
                Approver.document_id == document_id,
                Approver.approver_id == approver_id
            )
        )
        if existing:
            return existing  # уже есть
        approver = Approver(
            document_id=document_id,
            approver_id=approver_id,
            is_recipient=is_recipient
        )

        self.session.add(approver)
        await self.session.commit()

        return approver
