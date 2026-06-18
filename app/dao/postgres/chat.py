from sqlalchemy import and_, select, func, or_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import PostgresDao
from app.models.postgres.chat import Chat, ChatType
from app.models.postgres.chat_message import ChatMessage
from app.models.postgres.chat_message_read import ChatMessageRead
from app.models.postgres.chat_participant import ChatParticipant


class ChatDAO(PostgresDao):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Chat)

    async def get_or_create(self, user1_id: int, user2_id: int) -> Chat:
        lo, hi = sorted([user1_id, user2_id])

        stmt = select(Chat).where(
            Chat.type == ChatType.DIRECT,
            Chat.user1_id == lo,
            Chat.user2_id == hi,
        )
        result = await self.session.execute(stmt)
        chat = result.scalar_one_or_none()

        if chat:
            return chat

        chat = Chat(type=ChatType.DIRECT, user1_id=lo, user2_id=hi)
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

        read_exists = (
            select(ChatMessageRead.id)
            .where(
                ChatMessageRead.message_id == ChatMessage.id,
                ChatMessageRead.user_id == user_id,
            )
            .exists()
        )
        unread_subq = (
            select(
                ChatMessage.chat_id,
                func.count(ChatMessage.id).label("unread_count"),
            )
            .where(
                ChatMessage.sender_id != user_id,
                ~read_exists,
            )
            .group_by(ChatMessage.chat_id)
            .subquery()
        )

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

        stmt = (
            select(
                Chat,
                ChatMessage,
                func.coalesce(unread_subq.c.unread_count, 0).label("unread_count"),
            )
            .options(selectinload(ChatMessage.attachments))
            .where(
                or_(
                    and_(
                        or_(Chat.user1_id == user_id, Chat.user2_id == user_id),
                        Chat.id.not_in(hidden_direct_subq),
                    ),
                    visible_participant_exists,
                )
            )
            .outerjoin(last_msg_subq, last_msg_subq.c.chat_id == Chat.id)
            .outerjoin(ChatMessage, ChatMessage.id == last_msg_subq.c.last_message_id)
            .outerjoin(unread_subq, unread_subq.c.chat_id == Chat.id)
            .order_by(desc(func.coalesce(ChatMessage.created_at, Chat.created_at)))
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        chats = []
        for chat, last_message, unread_count in rows:
            participant_id = None
            if chat.type == ChatType.DIRECT:
                participant_id = chat.user2_id if chat.user1_id == user_id else chat.user1_id

            chats.append({
                "chat": chat,
                "last_message": last_message,
                "unread_count": unread_count,
                "participant_id": participant_id,
            })

        return chats
