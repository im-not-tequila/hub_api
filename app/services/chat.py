import json
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
from fastapi import HTTPException
from fastapi import UploadFile, WebSocket, WebSocketDisconnect

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.postgres.chat import ChatDAO
from app.dao.postgres.chat_message_attachment import ChatMessageAttachmentDAO
from app.dao.postgres.chat_message import ChatMessageDAO
from app.dao.mysql import TutorDAO
from app.core.settings import get_settings
from app.db.redis_connection import redis_client
from app.models.postgres import User as UserModel


class ChatService:
    MAX_ATTACHMENT_SIZE_BYTES = 20 * 1024 * 1024
    PRESENCE_CHANNEL = "chat:presence"
    ONLINE_USERS_KEY = "chat:online_users"

    def __init__(self, session_postgres: AsyncSession, session_nitro: AsyncSession):
        self.chat_dao = ChatDAO(session_postgres)
        self.message_dao = ChatMessageDAO(session_postgres)
        self.attachment_dao = ChatMessageAttachmentDAO(session_postgres)
        self.session_nitro = session_nitro

    async def get_chat_users(self, current_user: UserModel) -> list[dict]:
        stmt = (
            select(UserModel).where(
                UserModel.platonus_id.isnot(None),
                UserModel.is_student == False,
                UserModel.id != current_user.id,
            )
        )
        postgres_session = self.chat_dao.session
        result = await postgres_session.execute(stmt)
        pg_users = result.scalars().all()

        if not pg_users:
            return []

        platonus_to_pg = {u.platonus_id: u.id for u in pg_users}
        platonus_ids = list(platonus_to_pg.keys())

        tutor_dao = TutorDAO(self.session_nitro)
        tutor_rows = await tutor_dao.get_tutors_with_positions_by_ids(platonus_ids)

        result_list: list[dict] = []
        for tutor, position in tutor_rows:
            pg_user_id = platonus_to_pg.get(tutor.TutorID)
            if pg_user_id is None:
                continue

            firstname = (tutor.firstname or "").strip().capitalize()
            lastname = (tutor.lastname or "").strip().capitalize()
            patronymic = (tutor.patronymic or "").strip().capitalize()

            first_initial = f"{firstname[0].upper()}." if firstname else ""
            patronymic_initial = f"{patronymic[0].upper()}." if patronymic else ""
            shortname = f"{lastname} {first_initial}{patronymic_initial}".strip()

            post = position.NameRU if position else None

            result_list.append(
                {
                    "id": pg_user_id,
                    "firstname": firstname,
                    "lastname": lastname,
                    "shortname": shortname,
                    "is_online": False,
                    "last_seen": None,
                    "post": post,
                }
            )

        presence_map = await self._get_presence_map([user["id"] for user in result_list])
        for user in result_list:
            presence = presence_map.get(user["id"], {"is_online": False, "last_seen": None})
            user["is_online"] = presence["is_online"]
            user["last_seen"] = presence["last_seen"]

        return result_list

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
                "last_message": self._serialize_message(last_msg) if last_msg else None,
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
        await self._ensure_chat_access(current_user, chat_id)

        messages = await self.message_dao.get_messages(chat_id, limit, offset)
        return [self._serialize_message(m) for m in messages]

    async def send_message(
        self,
        current_user: UserModel,
        chat_id: int,
        text: str | None,
        attachment_ids: list[int] | None = None,
    ) -> dict:
        chat = await self._ensure_chat_access(current_user, chat_id)

        normalized_text = (text or "").strip() or None
        attachment_ids = list(dict.fromkeys(attachment_ids or []))
        if not normalized_text and not attachment_ids:
            raise HTTPException(
                status_code=400,
                detail="Message must contain text or at least one attachment",
            )

        pending_attachments = []
        if attachment_ids:
            pending_attachments = await self.attachment_dao.get_pending_by_ids_for_sender(
                chat_id=chat_id,
                uploader_id=current_user.id,
                attachment_ids=attachment_ids,
            )
            if len(pending_attachments) != len(attachment_ids):
                raise HTTPException(
                    status_code=400,
                    detail="Some attachments are invalid or already attached",
                )

        message = await self.message_dao.add(
            chat_id=chat_id,
            sender_id=current_user.id,
            text=normalized_text,
        )

        if attachment_ids:
            await self.attachment_dao.assign_to_message(attachment_ids, message.id)
            for attachment in pending_attachments:
                attachment.message_id = message.id
            message.attachments = pending_attachments

        recipient_id = chat.user2_id if chat.user1_id == current_user.id else chat.user1_id
        await redis_client.publish(
            f"chat:messages:{recipient_id}",
            json.dumps({
                "type": "new_message",
                "chat_id": chat_id,
                "message_id": message.id,
                "sender_id": current_user.id,
            }),
        )

        return self._serialize_message(message)

    async def upload_attachment(
        self,
        current_user: UserModel,
        chat_id: int,
        file: UploadFile,
    ) -> dict:
        await self._ensure_chat_access(current_user, chat_id)

        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=400, detail="Attachment file name is empty")

        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Attachment is empty")
        if len(file_content) > self.MAX_ATTACHMENT_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Attachment is too large. Max size is {self.MAX_ATTACHMENT_SIZE_BYTES // (1024 * 1024)} MB",
            )

        mime_type = (
            (file.content_type or "").strip().lower()
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )
        attachment_type = "image" if mime_type.startswith("image/") else "file"

        suffix = Path(filename).suffix
        if not suffix:
            guessed_suffix = mimetypes.guess_extension(mime_type or "")
            suffix = guessed_suffix or ""

        now = datetime.utcnow()
        storage_key = (
            Path("chat")
            / "attachments"
            / str(chat_id)
            / now.strftime("%Y")
            / now.strftime("%m")
            / f"{uuid.uuid4().hex}{suffix.lower()}"
        )
        storage_path = get_settings().STORAGE_DIRECTORY / storage_key
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(storage_path, "wb") as out_file:
            await out_file.write(file_content)

        attachment = await self.attachment_dao.add(
            chat_id=chat_id,
            message_id=None,
            uploader_id=current_user.id,
            type=attachment_type,
            mime_type=mime_type,
            original_name=filename,
            storage_key=str(storage_key),
            size_bytes=len(file_content),
            width=None,
            height=None,
        )

        return self._serialize_attachment(attachment)

    async def get_attachment_file(self, current_user: UserModel, attachment_id: int) -> dict:
        attachment = await self.attachment_dao.get_by_id(attachment_id)
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        await self._ensure_chat_access(current_user, attachment.chat_id)

        file_path = get_settings().STORAGE_DIRECTORY / attachment.storage_key
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Attachment file not found")

        return {
            "path": file_path,
            "filename": attachment.original_name,
            "mime_type": attachment.mime_type or "application/octet-stream",
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
        chat = await self._ensure_chat_access(current_user, chat_id)

        count = await self.message_dao.mark_as_read(chat_id, current_user.id)
        if count > 0:
            recipient_id = chat.user2_id if chat.user1_id == current_user.id else chat.user1_id
            await redis_client.publish(
                f"chat:messages:{recipient_id}",
                json.dumps({
                    "type": "messages_read",
                    "chat_id": chat_id,
                    "reader_id": current_user.id,
                    "marked_count": count,
                }),
            )
        return {"marked_count": count}

    async def handle_websocket(
        self,
        *,
        websocket: WebSocket,
        user: UserModel,
        refresh_token: str | None,
    ) -> None:
        if not refresh_token or not user:
            await websocket.close(code=1008)
            return

        await websocket.accept()

        pubsub = redis_client.pubsub()
        user_messages_channel = f"chat:messages:{user.id}"
        await pubsub.subscribe(user_messages_channel, self.PRESENCE_CHANNEL)
        await self._set_user_online(user.id)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except WebSocketDisconnect:
            pass
        finally:
            await pubsub.unsubscribe(user_messages_channel, self.PRESENCE_CHANNEL)
            await pubsub.close()
            await self._set_user_offline(user.id)

    async def _get_participants_map(self, user_ids: list[int]) -> dict:
        """Батчем получает данные участников: postgres id + ФИО/должность из MySQL."""
        from app.dao.postgres import UserDAO

        postgres_session = self.chat_dao.session
        default = lambda uid: {
            "id": uid,
            "firstname": "Неизвестный",
            "lastname": "Пользователь",
            "shortname": "Пользователь",
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

        presence_map = await self._get_presence_map(user_ids)
        for uid in user_ids:
            presence = presence_map.get(uid, {"is_online": False, "last_seen": None})
            users_map[uid]["is_online"] = presence["is_online"]
            users_map[uid]["last_seen"] = presence["last_seen"]

        return users_map

    async def _ensure_chat_access(self, current_user: UserModel, chat_id: int):
        chat = await self.chat_dao.get_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if current_user.id not in (chat.user1_id, chat.user2_id):
            raise HTTPException(status_code=403, detail="Access denied")
        return chat

    @staticmethod
    def _serialize_message(message) -> dict:
        return {
            "id": message.id,
            "chat_id": message.chat_id,
            "sender_id": message.sender_id,
            "text": message.text,
            "is_read": message.is_read,
            "created_at": message.created_at.isoformat() if message.created_at else None,
            "attachments": [
                ChatService._serialize_attachment(attachment)
                for attachment in message.attachments
            ],
        }

    @staticmethod
    def _serialize_attachment(attachment) -> dict:
        return {
            "id": attachment.id,
            "chat_id": attachment.chat_id,
            "message_id": attachment.message_id,
            "uploader_id": attachment.uploader_id,
            "type": attachment.type,
            "mime_type": attachment.mime_type,
            "original_name": attachment.original_name,
            "size_bytes": attachment.size_bytes,
            "width": attachment.width,
            "height": attachment.height,
            "url": f"/v1/chat/attachments/{attachment.id}",
            "created_at": attachment.created_at.isoformat() if attachment.created_at else None,
        }

    @staticmethod
    def _presence_count_key(user_id: int) -> str:
        return f"chat:presence:connections:{user_id}"

    @staticmethod
    def _last_seen_key(user_id: int) -> str:
        return f"chat:presence:last_seen:{user_id}"

    async def _get_presence_map(self, user_ids: list[int]) -> dict[int, dict]:
        if not user_ids:
            return {}

        unique_ids = list(dict.fromkeys(user_ids))
        pipeline = redis_client.pipeline()
        for uid in unique_ids:
            pipeline.sismember(self.ONLINE_USERS_KEY, str(uid))
            pipeline.get(self._last_seen_key(uid))
        raw = await pipeline.execute()

        result: dict[int, dict] = {}
        for index, uid in enumerate(unique_ids):
            is_online = bool(raw[index * 2])
            last_seen = raw[index * 2 + 1]
            result[uid] = {
                "is_online": is_online,
                "last_seen": None if is_online else last_seen,
            }
        return result

    async def _publish_presence_event(self, user_id: int, is_online: bool, last_seen: str | None):
        await redis_client.publish(
            self.PRESENCE_CHANNEL,
            json.dumps(
                {
                    "type": "presence_changed",
                    "user_id": user_id,
                    "is_online": is_online,
                    "last_seen": last_seen,
                }
            ),
        )

    async def _set_user_online(self, user_id: int):
        connection_count = await redis_client.incr(self._presence_count_key(user_id))
        await redis_client.sadd(self.ONLINE_USERS_KEY, str(user_id))
        await redis_client.delete(self._last_seen_key(user_id))

        if connection_count == 1:
            await self._publish_presence_event(user_id=user_id, is_online=True, last_seen=None)

    async def _set_user_offline(self, user_id: int):
        count_key = self._presence_count_key(user_id)
        current_count = await redis_client.get(count_key)
        if current_count is None:
            return

        connection_count = await redis_client.decr(count_key)
        if connection_count <= 0:
            await redis_client.delete(count_key)
            await redis_client.srem(self.ONLINE_USERS_KEY, str(user_id))
            last_seen = datetime.utcnow().isoformat()
            await redis_client.set(self._last_seen_key(user_id), last_seen)
            await self._publish_presence_event(
                user_id=user_id,
                is_online=False,
                last_seen=last_seen,
            )
