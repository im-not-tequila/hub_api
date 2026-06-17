import json
import mimetypes
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import HTTPException
from fastapi import UploadFile, WebSocket, WebSocketDisconnect

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.postgres.chat import ChatDAO
from app.dao.postgres.chat_message_read import ChatMessageReadDAO
from app.dao.postgres.chat_message_attachment import ChatMessageAttachmentDAO
from app.dao.postgres.chat_message import ChatMessageDAO
from app.dao.postgres.chat_participant import ChatParticipantDAO
from app.dao.mysql import TutorDAO
from app.core.settings import get_settings
from app.db.redis_connection import redis_client
from app.models.postgres import User as UserModel
from app.models.postgres.chat import Chat, ChatType
from app.models.postgres.chat_participant import ChatParticipant, ChatParticipantRole


class ChatService:
    MAX_ATTACHMENT_SIZE_BYTES = 20 * 1024 * 1024
    PRESENCE_CHANNEL = "chat:presence"
    PRESENCE_TTL_SECONDS = 45

    def __init__(self, session_postgres: AsyncSession, session_nitro: AsyncSession):
        self.chat_dao = ChatDAO(session_postgres)
        self.message_dao = ChatMessageDAO(session_postgres)
        self.message_read_dao = ChatMessageReadDAO(session_postgres)
        self.attachment_dao = ChatMessageAttachmentDAO(session_postgres)
        self.participant_dao = ChatParticipantDAO(session_postgres)
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

        result = []
        for row in chat_rows:
            result.append(
                await self._serialize_chat_summary(
                    row["chat"],
                    current_user.id,
                    last_message=row["last_message"],
                    unread_count=row["unread_count"],
                )
            )

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
        return [self._serialize_message(m, current_user.id) for m in messages]

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
        else:
            message.attachments = []
        message.reads = []

        await self._publish_to_chat_recipients(
            chat,
            current_user.id,
            {
                "type": "new_message",
                "chat_id": chat_id,
                "message_id": message.id,
                "sender_id": current_user.id,
            },
        )

        return self._serialize_message(message, current_user.id)

    async def forward_message(
        self,
        *,
        current_user: UserModel,
        message_id: int,
        target_chat_id: int | None = None,
        recipient_id: int | None = None,
    ) -> dict:
        source_message = await self.message_dao.get_by_id_with_attachments(message_id)
        if not source_message:
            raise HTTPException(status_code=404, detail="Source message not found")

        await self._ensure_chat_access(current_user, source_message.chat_id)
        target_chat = await self._resolve_forward_target_chat(
            current_user=current_user,
            target_chat_id=target_chat_id,
            recipient_id=recipient_id,
        )

        if source_message.text is None and not source_message.attachments:
            raise HTTPException(status_code=400, detail="Source message is empty")

        original_message_id = source_message.original_message_id or source_message.id
        original_sender_id = source_message.original_sender_id or source_message.sender_id
        forwarded_message = await self.message_dao.add(
            chat_id=target_chat.id,
            sender_id=current_user.id,
            text=source_message.text,
            forwarded_from_message_id=source_message.id,
            original_message_id=original_message_id,
            original_sender_id=original_sender_id,
        )

        copied_attachments = []
        if source_message.attachments:
            copied_attachments = await self.attachment_dao.bulk_add(
                [
                    {
                        "chat_id": target_chat.id,
                        "message_id": forwarded_message.id,
                        "uploader_id": current_user.id,
                        "type": attachment.type,
                        "mime_type": attachment.mime_type,
                        "original_name": attachment.original_name,
                        "storage_key": attachment.storage_key,
                        "size_bytes": attachment.size_bytes,
                        "width": attachment.width,
                        "height": attachment.height,
                    }
                    for attachment in source_message.attachments
                ]
            )
            forwarded_message.attachments = copied_attachments
        else:
            forwarded_message.attachments = []
        forwarded_message.reads = []

        await self._publish_to_chat_recipients(
            target_chat,
            current_user.id,
            {
                "type": "new_message",
                "chat_id": target_chat.id,
                "message_id": forwarded_message.id,
                "sender_id": current_user.id,
            },
        )

        return self._serialize_message(forwarded_message, current_user.id)

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
        await self._ensure_direct_participants(chat)

        return await self._serialize_chat_summary(
            chat,
            current_user.id,
            last_message=None,
            unread_count=0,
        )

    async def create_group_chat(
        self,
        current_user: UserModel,
        *,
        title: str,
        participant_ids: list[int],
        avatar_url: str | None = None,
    ) -> dict:
        participant_ids = list(dict.fromkeys([current_user.id, *participant_ids]))
        if len(participant_ids) < 2:
            raise HTTPException(status_code=400, detail="Group chat requires at least two participants")

        await self._ensure_users_exist(participant_ids)

        chat = Chat(
            type=ChatType.GROUP,
            title=title,
            avatar_url=avatar_url,
            creator_user_id=current_user.id,
        )
        self.chat_dao.session.add(chat)
        await self.chat_dao.session.flush()

        for user_id in participant_ids:
            self.chat_dao.session.add(
                ChatParticipant(
                    chat_id=chat.id,
                    user_id=user_id,
                    role=(
                        ChatParticipantRole.ADMIN
                        if user_id == current_user.id
                        else ChatParticipantRole.MEMBER
                    ),
                    added_by_user_id=current_user.id,
                )
            )

        await self.chat_dao.session.commit()
        await self.chat_dao.session.refresh(chat)

        await self._publish_to_chat_recipients(
            chat,
            current_user.id,
            {
                "type": "chat_created",
                "chat_id": chat.id,
                "chat_type": ChatType.GROUP.value,
            },
        )

        return await self._serialize_chat_summary(chat, current_user.id)

    async def update_group_chat(
        self,
        current_user: UserModel,
        chat_id: int,
        *,
        title: str | None,
        avatar_url: str | None,
    ) -> dict:
        chat = await self._ensure_group_admin(current_user, chat_id)
        if title is not None:
            chat.title = title
        if avatar_url is not None:
            chat.avatar_url = avatar_url

        await self.chat_dao.session.commit()
        await self.chat_dao.session.refresh(chat)
        await self._publish_to_chat_recipients(
            chat,
            current_user.id,
            {"type": "chat_updated", "chat_id": chat.id},
        )
        return await self._serialize_chat_summary(chat, current_user.id)

    async def get_chat_participants(self, current_user: UserModel, chat_id: int) -> list[dict]:
        await self._ensure_chat_access(current_user, chat_id)
        participants = await self.participant_dao.get_active_by_chat(chat_id)
        return await self._serialize_participants(participants)

    async def add_chat_participants(
        self,
        current_user: UserModel,
        chat_id: int,
        *,
        user_ids: list[int],
        role: str,
    ) -> list[dict]:
        chat = await self._ensure_group_admin(current_user, chat_id)
        user_ids = [user_id for user_id in list(dict.fromkeys(user_ids)) if user_id != current_user.id]
        if not user_ids:
            raise HTTPException(status_code=400, detail="No users to add")

        await self._ensure_users_exist(user_ids)

        target_role = ChatParticipantRole(role)
        for user_id in user_ids:
            await self.participant_dao.upsert_active(
                chat_id=chat_id,
                user_id=user_id,
                role=target_role,
                added_by_user_id=current_user.id,
            )

        await self._publish_to_chat_recipients(
            chat,
            current_user.id,
            {
                "type": "participants_added",
                "chat_id": chat.id,
                "user_ids": user_ids,
            },
        )
        return await self.get_chat_participants(current_user, chat_id)

    async def update_chat_participant_role(
        self,
        current_user: UserModel,
        chat_id: int,
        user_id: int,
        *,
        role: str,
    ) -> dict:
        await self._ensure_group_admin(current_user, chat_id)
        participant = await self.participant_dao.get_active_for_user(chat_id, user_id)
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")

        participant.role = ChatParticipantRole(role)
        await self.participant_dao.session.commit()
        await self.participant_dao.session.refresh(participant)
        return (await self._serialize_participants([participant]))[0]

    async def remove_chat_participant(
        self,
        current_user: UserModel,
        chat_id: int,
        user_id: int,
    ) -> dict:
        chat = await self._ensure_group_admin(current_user, chat_id)
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Admin cannot remove themself")

        participant = await self.participant_dao.get_active_for_user(chat_id, user_id)
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        if participant.role == ChatParticipantRole.ADMIN:
            active_participants = await self.participant_dao.get_active_by_chat(chat_id)
            admin_count = sum(1 for item in active_participants if item.role == ChatParticipantRole.ADMIN)
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove the last admin")

        removed = await self.participant_dao.deactivate(
            chat_id=chat_id,
            user_id=user_id,
            removed_by_user_id=current_user.id,
        )
        if not removed:
            raise HTTPException(status_code=404, detail="Participant not found")

        await self._publish_to_chat_recipients(
            chat,
            current_user.id,
            {
                "type": "participant_removed",
                "chat_id": chat.id,
                "user_id": user_id,
            },
        )
        await redis_client.publish(
            f"chat:messages:{user_id}",
            json.dumps({"type": "removed_from_chat", "chat_id": chat.id}),
        )
        return {"removed": True}

    async def mark_as_read(self, current_user: UserModel, chat_id: int) -> dict:
        chat = await self._ensure_chat_access(current_user, chat_id)

        count = await self.message_read_dao.mark_chat_as_read(chat_id, current_user.id)
        await self.message_dao.mark_as_read(chat_id, current_user.id)
        if count > 0:
            await self._publish_to_chat_recipients(
                chat,
                current_user.id,
                {
                    "type": "messages_read",
                    "chat_id": chat_id,
                    "reader_id": current_user.id,
                    "marked_count": count,
                },
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
            async def _forward_pubsub_to_socket():
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        await websocket.send_text(message["data"])

            async def _wait_for_disconnect():
                while True:
                    await websocket.receive_text()

            async def _presence_heartbeat():
                while True:
                    await asyncio.sleep(self.PRESENCE_TTL_SECONDS // 3)
                    await self._refresh_presence_lease(user.id)

            forward_task = asyncio.create_task(_forward_pubsub_to_socket())
            disconnect_task = asyncio.create_task(_wait_for_disconnect())
            heartbeat_task = asyncio.create_task(_presence_heartbeat())

            done, pending = await asyncio.wait(
                {forward_task, disconnect_task, heartbeat_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc and not isinstance(exc, WebSocketDisconnect):
                    raise exc
        except WebSocketDisconnect:
            pass
        finally:
            await pubsub.unsubscribe(user_messages_channel, self.PRESENCE_CHANNEL)
            await pubsub.close()
            await self._set_user_offline(user.id)

    async def _serialize_chat_summary(
        self,
        chat: Chat,
        current_user_id: int,
        *,
        last_message=None,
        unread_count: int | None = None,
    ) -> dict:
        participants = await self.participant_dao.get_active_by_chat(chat.id)
        participant_payloads = await self._serialize_participants(participants)
        participant_by_user_id = {
            payload["user"]["id"]: payload
            for payload in participant_payloads
        }
        current_participant = participant_by_user_id.get(current_user_id)

        direct_participant = None
        if chat.type == ChatType.DIRECT:
            other_user_id = chat.user2_id if chat.user1_id == current_user_id else chat.user1_id
            if other_user_id is not None:
                direct_participant = (await self._get_participants_map([other_user_id])).get(other_user_id)

        if unread_count is None:
            unread_count = await self.message_read_dao.count_unread(chat.id, current_user_id)

        return {
            "id": chat.id,
            "type": chat.type.value,
            "title": chat.title,
            "avatar_url": chat.avatar_url,
            "creator_user_id": chat.creator_user_id,
            "participant": direct_participant,
            "participants": participant_payloads,
            "my_role": current_participant["role"] if current_participant else None,
            "last_message": (
                self._serialize_message(last_message, current_user_id)
                if last_message
                else None
            ),
            "unread_count": unread_count,
        }

    async def _serialize_participants(self, participants: list[ChatParticipant]) -> list[dict]:
        user_ids = [participant.user_id for participant in participants]
        users_map = await self._get_participants_map(user_ids)

        return [
            {
                "user": users_map.get(participant.user_id),
                "role": participant.role.value,
                "is_active": participant.is_active,
                "added_by_user_id": participant.added_by_user_id,
                "removed_by_user_id": participant.removed_by_user_id,
                "removed_at": participant.removed_at.isoformat() if participant.removed_at else None,
                "created_at": participant.created_at.isoformat() if participant.created_at else None,
            }
            for participant in participants
        ]

    async def _ensure_users_exist(self, user_ids: list[int]) -> None:
        if not user_ids:
            return

        result = await self.chat_dao.session.execute(
            select(UserModel.id).where(UserModel.id.in_(user_ids))
        )
        found_ids = set(result.scalars().all())
        missing_ids = [user_id for user_id in user_ids if user_id not in found_ids]
        if missing_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Users not found: {', '.join(map(str, missing_ids))}",
            )

    async def _ensure_direct_participants(self, chat: Chat) -> None:
        if chat.type != ChatType.DIRECT or chat.user1_id is None or chat.user2_id is None:
            return

        for user_id in (chat.user1_id, chat.user2_id):
            if not await self.participant_dao.get_for_user(chat.id, user_id):
                self.chat_dao.session.add(
                    ChatParticipant(
                        chat_id=chat.id,
                        user_id=user_id,
                        role=ChatParticipantRole.MEMBER,
                        added_by_user_id=None,
                    )
                )
        await self.chat_dao.session.commit()

    async def _get_chat_recipient_ids(self, chat: Chat, sender_id: int) -> list[int]:
        participant_ids = await self.participant_dao.get_active_user_ids(chat.id)
        if not participant_ids and chat.type == ChatType.DIRECT:
            participant_ids = [
                user_id
                for user_id in (chat.user1_id, chat.user2_id)
                if user_id is not None
            ]
        return [user_id for user_id in participant_ids if user_id != sender_id]

    async def _publish_to_chat_recipients(
        self,
        chat: Chat,
        sender_id: int,
        payload: dict,
    ) -> None:
        recipient_ids = await self._get_chat_recipient_ids(chat, sender_id)
        if not recipient_ids:
            return

        message = json.dumps(payload)
        for recipient_id in recipient_ids:
            await redis_client.publish(f"chat:messages:{recipient_id}", message)

    async def _get_participants_map(self, user_ids: list[int]) -> dict:
        """Батчем получает данные участников: postgres id + ФИО/должность из MySQL."""
        from app.dao.postgres import UserDAO

        if not user_ids:
            return {}

        user_ids = list(dict.fromkeys(user_ids))
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
            limit=len(user_ids),
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

        if current_user.id in (chat.user1_id, chat.user2_id):
            return chat

        participant = await self.participant_dao.get_active_for_user(chat_id, current_user.id)
        if not participant:
            raise HTTPException(status_code=403, detail="Access denied")
        return chat

    async def _ensure_group_admin(self, current_user: UserModel, chat_id: int) -> Chat:
        chat = await self._ensure_chat_access(current_user, chat_id)
        if chat.type != ChatType.GROUP:
            raise HTTPException(status_code=400, detail="Operation is available only for group chats")

        participant = await self.participant_dao.get_active_for_user(chat_id, current_user.id)
        if not participant or participant.role != ChatParticipantRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only chat admin can perform this action")
        return chat

    async def _resolve_forward_target_chat(
        self,
        *,
        current_user: UserModel,
        target_chat_id: int | None,
        recipient_id: int | None,
    ):
        if target_chat_id is not None:
            return await self._ensure_chat_access(current_user, target_chat_id)

        if recipient_id is None:
            raise HTTPException(
                status_code=400,
                detail="Either target_chat_id or recipient_id must be provided",
            )
        if recipient_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot forward message to yourself")
        return await self.chat_dao.get_or_create(current_user.id, recipient_id)

    @staticmethod
    def _serialize_message(message, current_user_id: int | None = None) -> dict:
        is_read = message.is_read
        if current_user_id is not None:
            is_read = (
                message.sender_id == current_user_id
                or any(read.user_id == current_user_id for read in getattr(message, "reads", []))
            )

        return {
            "id": message.id,
            "chat_id": message.chat_id,
            "sender_id": message.sender_id,
            "text": message.text,
            "is_read": is_read,
            "is_forwarded": message.forwarded_from_message_id is not None,
            "forwarded_from_message_id": message.forwarded_from_message_id,
            "original_message_id": message.original_message_id,
            "original_sender_id": message.original_sender_id,
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
            pipeline.get(self._presence_count_key(uid))
            pipeline.get(self._last_seen_key(uid))
            pipeline.ttl(self._presence_count_key(uid))
        raw = await pipeline.execute()

        result: dict[int, dict] = {}
        for index, uid in enumerate(unique_ids):
            raw_count = raw[index * 3]
            count = int(raw_count) if raw_count else 0
            is_online = count > 0
            last_seen = raw[index * 3 + 1]
            ttl_raw = raw[index * 3 + 2]
            ttl = int(ttl_raw) if ttl_raw is not None else -2

            # Heal stale presence keys left without TTL by older logic.
            # This prevents users from hanging "online" indefinitely.
            if is_online and ttl < 0:
                await redis_client.expire(
                    self._presence_count_key(uid),
                    self.PRESENCE_TTL_SECONDS,
                )
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
        count_key = self._presence_count_key(user_id)
        last_seen_key = self._last_seen_key(user_id)
        pipeline = redis_client.pipeline(transaction=True)
        pipeline.incr(count_key)
        pipeline.expire(count_key, self.PRESENCE_TTL_SECONDS)
        pipeline.delete(last_seen_key)
        result = await pipeline.execute()
        connection_count = int(result[0])

        if connection_count == 1:
            await self._publish_presence_event(user_id=user_id, is_online=True, last_seen=None)

    async def _refresh_presence_lease(self, user_id: int):
        await redis_client.expire(self._presence_count_key(user_id), self.PRESENCE_TTL_SECONDS)

    async def _set_user_offline(self, user_id: int):
        count_key = self._presence_count_key(user_id)
        current_count = await redis_client.get(count_key)
        if current_count is None:
            return

        connection_count = await redis_client.decr(count_key)
        if connection_count <= 0:
            await redis_client.delete(count_key)
            last_seen = datetime.now(timezone.utc).isoformat()
            await redis_client.set(self._last_seen_key(user_id), last_seen)
            await self._publish_presence_event(
                user_id=user_id,
                is_online=False,
                last_seen=last_seen,
            )
