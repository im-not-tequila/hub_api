from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import PostgresDao
from app.models.postgres.chat_message_user_deletion import ChatMessageUserDeletion


class ChatMessageUserDeletionDAO(PostgresDao):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ChatMessageUserDeletion)

    async def exists(self, message_id: int, user_id: int) -> bool:
        stmt = select(ChatMessageUserDeletion.id).where(
            ChatMessageUserDeletion.message_id == message_id,
            ChatMessageUserDeletion.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add_if_absent(self, message_id: int, user_id: int) -> bool:
        """Добавляет запись, если её ещё нет. Возвращает True если запись была создана."""
        if await self.exists(message_id, user_id):
            return False
        self.session.add(ChatMessageUserDeletion(message_id=message_id, user_id=user_id))
        await self.session.commit()
        return True

    async def get_deleted_message_ids(self, user_id: int, message_ids: list[int]) -> set[int]:
        """Возвращает подмножество message_ids, скрытых данным пользователем."""
        if not message_ids:
            return set()
        stmt = select(ChatMessageUserDeletion.message_id).where(
            ChatMessageUserDeletion.user_id == user_id,
            ChatMessageUserDeletion.message_id.in_(message_ids),
        )
        result = await self.session.execute(stmt)
        return set(result.scalars().all())
