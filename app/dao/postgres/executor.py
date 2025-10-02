from sqlalchemy import update

from datetime import datetime, UTC

from app.dao.base import PostgresDao
from app.models.postgres import Executor, ExecutorStatus


class ExecutorDAO(PostgresDao):
    def __init__(self, session):
        super().__init__(session, Executor)

    async def set_status(
            self,
            document_id: int,
            executor_id: int,
            status: ExecutorStatus
    ) -> Executor | None:
        stmt = (
            update(Executor)
            .where(
                Executor.document_id == document_id,
                Executor.executor_id == executor_id
            )
            .values(
                status=status,
                completed_at=datetime.now(UTC) if status == ExecutorStatus.COMPLETED else None
            )
            .returning(Executor)
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.scalar_one_or_none()
