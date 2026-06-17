from sqlalchemy import select, update as sa_update, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dao.base import PostgresDao
from app.models.postgres.chat_message import ChatMessage


class ChatMessageDAO(PostgresDao):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ChatMessage)

    async def get_messages(
        self,
        chat_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .options(
                selectinload(ChatMessage.attachments),
                selectinload(ChatMessage.reads),
            )
            .where(ChatMessage.chat_id == chat_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def get_by_id_with_attachments(self, message_id: int) -> ChatMessage | None:
        stmt = (
            select(ChatMessage)
            .options(
                selectinload(ChatMessage.attachments),
                selectinload(ChatMessage.reads),
            )
            .where(ChatMessage.id == message_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_as_read(self, chat_id: int, reader_id: int) -> int:
        stmt = (
            sa_update(ChatMessage)
            .where(
                and_(
                    ChatMessage.chat_id == chat_id,
                    ChatMessage.sender_id != reader_id,
                    ChatMessage.is_read == False,
                )
            )
            .values(is_read=True)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
