from sqlalchemy import select, func, case, and_, or_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import PostgresDao
from app.models.postgres.chat import Chat
from app.models.postgres.chat_message import ChatMessage


class ChatDAO(PostgresDao):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Chat)

    async def get_or_create(self, user1_id: int, user2_id: int) -> Chat:
        lo, hi = sorted([user1_id, user2_id])

        stmt = select(Chat).where(Chat.user1_id == lo, Chat.user2_id == hi)
        result = await self.session.execute(stmt)
        chat = result.scalar_one_or_none()

        if chat:
            return chat

        chat = Chat(user1_id=lo, user2_id=hi)
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def get_user_chats(self, user_id: int) -> list[dict]:
        last_msg_subq = (
            select(
                ChatMessage.chat_id,
                func.max(ChatMessage.id).label("last_message_id"),
            )
            .group_by(ChatMessage.chat_id)
            .subquery()
        )

        unread_subq = (
            select(
                ChatMessage.chat_id,
                func.count(ChatMessage.id).label("unread_count"),
            )
            .where(ChatMessage.is_read == False, ChatMessage.sender_id != user_id)
            .group_by(ChatMessage.chat_id)
            .subquery()
        )

        stmt = (
            select(
                Chat,
                ChatMessage,
                func.coalesce(unread_subq.c.unread_count, 0).label("unread_count"),
            )
            .where(or_(Chat.user1_id == user_id, Chat.user2_id == user_id))
            .outerjoin(last_msg_subq, last_msg_subq.c.chat_id == Chat.id)
            .outerjoin(ChatMessage, ChatMessage.id == last_msg_subq.c.last_message_id)
            .outerjoin(unread_subq, unread_subq.c.chat_id == Chat.id)
            .order_by(desc(func.coalesce(ChatMessage.created_at, Chat.created_at)))
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        chats = []
        for chat, last_message, unread_count in rows:
            participant_id = chat.user2_id if chat.user1_id == user_id else chat.user1_id
            chats.append({
                "chat": chat,
                "last_message": last_message,
                "unread_count": unread_count,
                "participant_id": participant_id,
            })

        return chats
