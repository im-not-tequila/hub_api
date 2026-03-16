from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.postgres.chat import ChatDAO
from app.dao.postgres.chat_message import ChatMessageDAO
from app.dao.mysql import TutorDAO
from app.models.postgres import User as UserModel


class ChatService:
    def __init__(self, session_postgres: AsyncSession, session_nitro: AsyncSession):
        self.chat_dao = ChatDAO(session_postgres)
        self.message_dao = ChatMessageDAO(session_postgres)
        self.session_nitro = session_nitro

    async def get_chats(self, current_user: UserModel) -> list[dict]:
        chat_rows = await self.chat_dao.get_user_chats(current_user.id)

        if not chat_rows:
            return []

        participant_ids = [r["participant_id"] for r in chat_rows]
        participants_map = await self._get_participants_map(participant_ids)

        result = []
        for row in chat_rows:
            participant = participants_map.get(row["participant_id"])
            last_msg = row["last_message"]

            result.append({
                "id": row["chat"].id,
                "participant": participant,
                "last_message": {
                    "id": last_msg.id,
                    "chat_id": last_msg.chat_id,
                    "sender_id": last_msg.sender_id,
                    "text": last_msg.text,
                    "is_read": last_msg.is_read,
                    "created_at": last_msg.created_at.isoformat() if last_msg.created_at else None,
                } if last_msg else None,
                "unread_count": row["unread_count"],
            })

        return result

    async def get_messages(
        self,
        current_user: UserModel,
        chat_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        chat = await self.chat_dao.get_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        if current_user.id not in (chat.user1_id, chat.user2_id):
            raise HTTPException(status_code=403, detail="Access denied")

        messages = await self.message_dao.get_messages(chat_id, limit, offset)
        return [
            {
                "id": m.id,
                "chat_id": m.chat_id,
                "sender_id": m.sender_id,
                "text": m.text,
                "is_read": m.is_read,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]

    async def send_message(self, current_user: UserModel, chat_id: int, text: str) -> dict:
        chat = await self.chat_dao.get_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        if current_user.id not in (chat.user1_id, chat.user2_id):
            raise HTTPException(status_code=403, detail="Access denied")

        message = await self.message_dao.add(
            chat_id=chat_id,
            sender_id=current_user.id,
            text=text,
        )

        return {
            "id": message.id,
            "chat_id": message.chat_id,
            "sender_id": message.sender_id,
            "text": message.text,
            "is_read": message.is_read,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }

    async def create_chat(self, current_user: UserModel, participant_id: int) -> dict:
        if current_user.id == participant_id:
            raise HTTPException(status_code=400, detail="Cannot create chat with yourself")

        chat = await self.chat_dao.get_or_create(current_user.id, participant_id)
        participant = await self._get_participants_map([participant_id])

        return {
            "id": chat.id,
            "participant": participant.get(participant_id),
            "last_message": None,
            "unread_count": 0,
        }

    async def mark_as_read(self, current_user: UserModel, chat_id: int) -> dict:
        chat = await self.chat_dao.get_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        if current_user.id not in (chat.user1_id, chat.user2_id):
            raise HTTPException(status_code=403, detail="Access denied")

        count = await self.message_dao.mark_as_read(chat_id, current_user.id)
        return {"marked_count": count}

    async def _get_participants_map(self, user_ids: list[int]) -> dict:
        """Батчем получает данные участников: postgres id + ФИО/должность из MySQL."""
        from app.dao.postgres import UserDAO

        postgres_session = self.chat_dao.session
        default = lambda uid: {
            "id": uid,
            "firstname": "Неизвестный",
            "lastname": "Пользователь",
            "shortname": "Пользователь",
            "avatar": None,
            "is_online": False,
            "last_seen": None,
            "post": None,
        }

        user_dao = UserDAO(postgres_session)
        pg_users = await user_dao.get_all_filtered(
            filters={UserModel.id: user_ids},
        )

        platonus_to_pg = {}
        users_map = {}
        for u in pg_users:
            if u.platonus_id:
                platonus_to_pg[u.platonus_id] = u.id
            else:
                users_map[u.id] = default(u.id)

        if platonus_to_pg:
            tutor_dao = TutorDAO(self.session_nitro)
            tutor_rows = await tutor_dao.get_tutors_with_positions_by_ids(
                list(platonus_to_pg.keys())
            )

            found_platonus = set()
            for tutor, position in tutor_rows:
                pg_id = platonus_to_pg.get(tutor.TutorID)
                if pg_id is None:
                    continue
                found_platonus.add(tutor.TutorID)

                firstname = (tutor.firstname or "").strip().capitalize()
                lastname = (tutor.lastname or "").strip().capitalize()
                patronymic = (tutor.patronymic or "").strip().capitalize()

                first_initial = f"{firstname[0].upper()}." if firstname else ""
                patronymic_initial = f"{patronymic[0].upper()}." if patronymic else ""
                shortname = f"{lastname} {first_initial}{patronymic_initial}".strip()

                users_map[pg_id] = {
                    "id": pg_id,
                    "firstname": firstname,
                    "lastname": lastname,
                    "shortname": shortname,
                    "avatar": None,
                    "is_online": False,
                    "last_seen": None,
                    "post": position.NameRU if position else None,
                }

            for plat_id, pg_id in platonus_to_pg.items():
                if plat_id not in found_platonus:
                    users_map[pg_id] = default(pg_id)

        for uid in user_ids:
            if uid not in users_map:
                users_map[uid] = default(uid)

        return users_map
