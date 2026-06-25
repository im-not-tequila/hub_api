from datetime import datetime, timezone

from sqlalchemy import select, update as sa_update, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dao.base import PostgresDao
from app.models.postgres.chat import Chat
from app.models.postgres.chat_message import ChatMessage
from app.models.postgres.chat_message_user_deletion import ChatMessageUserDeletion
from app.models.postgres.chat_participant import ChatParticipant


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
            .where(
                ChatMessage.chat_id == chat_id,
                ChatMessage.is_deleted == False,
            )
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(reversed(result.scalars().all()))

    def _user_messages_base_stmt(self, user_id: int):
        visible_participant_exists = (
            select(ChatParticipant.id)
            .where(
                ChatParticipant.chat_id == Chat.id,
                ChatParticipant.user_id == user_id,
                ChatParticipant.is_active == True,
                ChatParticipant.chat_hidden_at.is_(None),
            )
            .exists()
        )
        hidden_direct_subq = (
            select(ChatParticipant.chat_id)
            .where(
                ChatParticipant.user_id == user_id,
                ChatParticipant.chat_hidden_at.isnot(None),
            )
        )
        user_deleted_exists = (
            select(ChatMessageUserDeletion.id)
            .where(
                ChatMessageUserDeletion.message_id == ChatMessage.id,
                ChatMessageUserDeletion.user_id == user_id,
            )
            .exists()
        )
        chat_access = or_(
            and_(
                or_(Chat.user1_id == user_id, Chat.user2_id == user_id),
                Chat.id.not_in(hidden_direct_subq),
            ),
            visible_participant_exists,
        )

        return (
            select(ChatMessage)
            .join(Chat, ChatMessage.chat_id == Chat.id)
            .options(
                selectinload(ChatMessage.attachments),
                selectinload(ChatMessage.reads),
            )
            .where(
                ChatMessage.is_deleted == False,
                ~user_deleted_exists,
                chat_access,
            )
        )

    async def get_incoming_messages(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatMessage]:
        stmt = (
            self._user_messages_base_stmt(user_id)
            .where(ChatMessage.sender_id != user_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_outgoing_messages(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatMessage]:
        stmt = (
            self._user_messages_base_stmt(user_id)
            .where(ChatMessage.sender_id == user_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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

    async def soft_delete_for_all(self, message_id: int, deleted_by_user_id: int) -> bool:
        """Помечает сообщение удалённым для всех. Возвращает True если запись была найдена."""
        stmt = (
            sa_update(ChatMessage)
            .where(
                ChatMessage.id == message_id,
                ChatMessage.is_deleted == False,
            )
            .values(
                is_deleted=True,
                deleted_at=datetime.now(timezone.utc),
                deleted_by_user_id=deleted_by_user_id,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return bool(result.rowcount)

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
