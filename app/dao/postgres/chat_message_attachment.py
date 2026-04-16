from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import PostgresDao
from app.models.postgres.chat_message_attachment import ChatMessageAttachment


class ChatMessageAttachmentDAO(PostgresDao):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ChatMessageAttachment)

    async def get_pending_by_ids_for_sender(
        self,
        *,
        chat_id: int,
        uploader_id: int,
        attachment_ids: list[int],
    ) -> list[ChatMessageAttachment]:
        if not attachment_ids:
            return []

        stmt = (
            select(ChatMessageAttachment)
            .where(
                ChatMessageAttachment.id.in_(attachment_ids),
                ChatMessageAttachment.chat_id == chat_id,
                ChatMessageAttachment.uploader_id == uploader_id,
                ChatMessageAttachment.message_id.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def assign_to_message(self, attachment_ids: list[int], message_id: int) -> int:
        if not attachment_ids:
            return 0

        stmt = (
            sa_update(ChatMessageAttachment)
            .where(ChatMessageAttachment.id.in_(attachment_ids))
            .values(message_id=message_id)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount or 0
