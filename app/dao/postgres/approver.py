from sqlalchemy import update

from datetime import datetime, UTC

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
                status=status,
                signed_at=datetime.now(UTC) if status == ApproverStatus.SIGNED else None
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
