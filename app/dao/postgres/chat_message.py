from sqlalchemy import select, update as sa_update, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

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
            .where(ChatMessage.chat_id == chat_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(reversed(result.scalars().all()))

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
