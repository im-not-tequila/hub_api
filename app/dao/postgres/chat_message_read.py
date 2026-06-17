from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import PostgresDao
from app.models.postgres.chat_message import ChatMessage
from app.models.postgres.chat_message_read import ChatMessageRead


class ChatMessageReadDAO(PostgresDao):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ChatMessageRead)

    async def count_unread(self, chat_id: int, user_id: int) -> int:
        read_exists = (
            select(ChatMessageRead.id)
            .where(
                ChatMessageRead.message_id == ChatMessage.id,
                ChatMessageRead.user_id == user_id,
            )
            .exists()
        )
        stmt = select(func.count(ChatMessage.id)).where(
            ChatMessage.chat_id == chat_id,
            ChatMessage.sender_id != user_id,
            ~read_exists,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def mark_chat_as_read(self, chat_id: int, user_id: int) -> int:
        read_exists = (
            select(ChatMessageRead.id)
            .where(
                ChatMessageRead.message_id == ChatMessage.id,
                ChatMessageRead.user_id == user_id,
            )
            .exists()
        )
        unread_stmt = select(ChatMessage.id).where(
            ChatMessage.chat_id == chat_id,
            ChatMessage.sender_id != user_id,
            ~read_exists,
        )
        result = await self.session.execute(unread_stmt)
        message_ids = result.scalars().all()
        if not message_ids:
            return 0

        stmt = (
            insert(ChatMessageRead)
            .values(
                [
                    {
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "user_id": user_id,
                    }
                    for message_id in message_ids
                ]
            )
            .on_conflict_do_nothing(
                index_elements=["message_id", "user_id"],
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return len(message_ids)
