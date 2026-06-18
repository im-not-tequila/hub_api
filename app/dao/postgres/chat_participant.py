from datetime import datetime, timezone

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import PostgresDao
from app.models.postgres.chat_participant import ChatParticipant, ChatParticipantRole


class ChatParticipantDAO(PostgresDao):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ChatParticipant)

    async def get_for_user(self, chat_id: int, user_id: int) -> ChatParticipant | None:
        stmt = select(ChatParticipant).where(
            ChatParticipant.chat_id == chat_id,
            ChatParticipant.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_user(self, chat_id: int, user_id: int) -> ChatParticipant | None:
        stmt = select(ChatParticipant).where(
            ChatParticipant.chat_id == chat_id,
            ChatParticipant.user_id == user_id,
            ChatParticipant.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_chat(self, chat_id: int) -> list[ChatParticipant]:
        stmt = (
            select(ChatParticipant)
            .where(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.is_active == True,
            )
            .order_by(ChatParticipant.created_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_user_ids(self, chat_id: int) -> list[int]:
        stmt = select(ChatParticipant.user_id).where(
            ChatParticipant.chat_id == chat_id,
            ChatParticipant.is_active == True,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_active(
        self,
        *,
        chat_id: int,
        user_id: int,
        role: ChatParticipantRole,
        added_by_user_id: int | None,
    ) -> ChatParticipant:
        participant = await self.get_for_user(chat_id, user_id)
        if participant:
            participant.role = role
            participant.is_active = True
            participant.added_by_user_id = added_by_user_id
            participant.removed_by_user_id = None
            participant.removed_at = None
        else:
            participant = ChatParticipant(
                chat_id=chat_id,
                user_id=user_id,
                role=role,
                added_by_user_id=added_by_user_id,
            )
            self.session.add(participant)

        await self.session.commit()
        await self.session.refresh(participant)
        return participant

    async def set_chat_hidden(self, *, chat_id: int, user_id: int) -> bool:
        """Помечает чат скрытым для пользователя. Возвращает True если запись была найдена."""
        stmt = (
            sa_update(ChatParticipant)
            .where(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.user_id == user_id,
            )
            .values(chat_hidden_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount)

    async def unhide_chat(self, *, chat_id: int, user_id: int) -> None:
        """Снимает скрытие чата при отправке нового сообщения."""
        stmt = (
            sa_update(ChatParticipant)
            .where(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.user_id == user_id,
                ChatParticipant.chat_hidden_at.isnot(None),
            )
            .values(chat_hidden_at=None)
        )
        await self.session.execute(stmt)

    async def deactivate(self, *, chat_id: int, user_id: int, removed_by_user_id: int) -> bool:
        stmt = (
            sa_update(ChatParticipant)
            .where(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.user_id == user_id,
                ChatParticipant.is_active == True,
            )
            .values(
                is_active=False,
                removed_by_user_id=removed_by_user_id,
                removed_at=datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount)
