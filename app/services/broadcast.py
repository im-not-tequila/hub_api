from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import json
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles

from app.dao.postgres.broadcast_group import BroadcastGroupDAO
from app.dao.postgres.chat import ChatDAO
from app.dao.postgres.chat_message import ChatMessageDAO
from app.dao.postgres.chat_message_attachment import ChatMessageAttachmentDAO
from app.dao.mysql import TutorDAO
from app.models.postgres import User as UserModel
from app.models.postgres.broadcast_group import BroadcastGroup
from app.models.postgres.broadcast_group_member import BroadcastGroupMember
from app.models.postgres.role import Role
from app.db.redis_connection import redis_client
from app.core.settings import get_settings
from app.services.chat import ChatService


def _is_system_admin(user: UserModel) -> bool:
    """Системный администратор — любой нестудент с назначенными ролями."""
    return not user.is_student and bool(user.user_roles)


class BroadcastService:
    MAX_ATTACHMENT_SIZE_BYTES = ChatService.MAX_ATTACHMENT_SIZE_BYTES

    def __init__(
        self,
        session_postgres: AsyncSession,
        session_nitro: AsyncSession,
    ):
        self.session = session_postgres
        self.broadcast_dao = BroadcastGroupDAO(session_postgres)
        self.chat_dao = ChatDAO(session_postgres)
        self.message_dao = ChatMessageDAO(session_postgres)
        self.attachment_dao = ChatMessageAttachmentDAO(session_postgres)
        self.session_nitro = session_nitro

    # ------------------------------------------------------------------ #
    #  Группы
    # ------------------------------------------------------------------ #

    async def get_all_roles(self) -> list[Role]:
        """Возвращает все активные роли для выбора при управлении группой."""
        result = await self.session.execute(
            select(Role).where(Role.is_active == True).order_by(Role.name_ru)
        )
        return list(result.scalars().all())

    async def get_groups(self, current_user: UserModel) -> list[dict]:
        is_admin = _is_system_admin(current_user)
        groups = await self.broadcast_dao.get_groups_for_user(current_user.id, is_admin)
        return [self._serialize_group(g) for g in groups]

    async def get_group(self, current_user: UserModel, group_id: int) -> dict:
        group = await self._get_accessible_group(current_user, group_id)
        return self._serialize_group(group)

    async def create_group(
        self,
        current_user: UserModel,
        *,
        name: str,
        description: str | None,
        member_ids: list[int],
    ) -> dict:
        self._require_admin(current_user)

        if member_ids:
            await self._ensure_users_exist(member_ids)

        group = BroadcastGroup(
            name=name,
            description=description,
            created_by_user_id=current_user.id,
        )
        self.session.add(group)
        await self.session.flush()

        for user_id in list(dict.fromkeys(member_ids)):
            self.session.add(
                BroadcastGroupMember(
                    group_id=group.id,
                    user_id=user_id,
                    added_by_user_id=current_user.id,
                )
            )

        await self.session.commit()
        await self.session.refresh(group)
        return self._serialize_group(group)

    async def update_group(
        self,
        current_user: UserModel,
        group_id: int,
        *,
        name: str | None,
        description: str | None,
    ) -> dict:
        self._require_admin(current_user)
        group = await self._get_group_or_404(group_id)

        if name is not None:
            group.name = name
        if description is not None:
            group.description = description

        await self.session.commit()
        await self.session.refresh(group)
        return self._serialize_group(group)

    async def delete_group(self, current_user: UserModel, group_id: int) -> dict:
        self._require_admin(current_user)
        group = await self._get_group_or_404(group_id)
        await self.session.delete(group)
        await self.session.commit()
        return {"deleted": True}

    # ------------------------------------------------------------------ #
    #  Участники группы
    # ------------------------------------------------------------------ #

    async def get_members(self, current_user: UserModel, group_id: int) -> list[dict]:
        await self._get_accessible_group(current_user, group_id)
        members = await self._load_members(group_id)
        return await self._serialize_members(members)

    async def add_members(
        self,
        current_user: UserModel,
        group_id: int,
        user_ids: list[int],
    ) -> list[dict]:
        self._require_admin(current_user)
        await self._get_group_or_404(group_id)

        user_ids = list(dict.fromkeys(user_ids))
        await self._ensure_users_exist(user_ids)

        for user_id in user_ids:
            await self.broadcast_dao.add_member(
                group_id=group_id,
                user_id=user_id,
                added_by_user_id=current_user.id,
            )

        await self.session.commit()
        members = await self._load_members(group_id)
        return await self._serialize_members(members)

    async def remove_member(
        self,
        current_user: UserModel,
        group_id: int,
        user_id: int,
    ) -> dict:
        self._require_admin(current_user)
        await self._get_group_or_404(group_id)

        removed = await self.broadcast_dao.remove_member(group_id, user_id)
        await self.session.commit()
        if not removed:
            raise HTTPException(status_code=404, detail="Member not found in group")
        return {"removed": True}

    # ------------------------------------------------------------------ #
    #  Роли с доступом к группе
    # ------------------------------------------------------------------ #

    async def get_allowed_roles(self, current_user: UserModel, group_id: int) -> list[dict]:
        self._require_admin(current_user)
        group = await self._get_group_or_404(group_id)
        return [self._serialize_role(gr.role) for gr in group.allowed_roles]

    async def add_allowed_role(
        self,
        current_user: UserModel,
        group_id: int,
        role_id: int,
    ) -> dict:
        self._require_admin(current_user)
        await self._get_group_or_404(group_id)
        await self._ensure_role_exists(role_id)

        gr = await self.broadcast_dao.add_role(group_id, role_id)
        await self.session.commit()
        await self.session.refresh(gr)
        return self._serialize_role(gr.role)

    async def remove_allowed_role(
        self,
        current_user: UserModel,
        group_id: int,
        role_id: int,
    ) -> dict:
        self._require_admin(current_user)
        await self._get_group_or_404(group_id)

        removed = await self.broadcast_dao.remove_role(group_id, role_id)
        await self.session.commit()
        if not removed:
            raise HTTPException(status_code=404, detail="Role not found in group")
        return {"removed": True}

    # ------------------------------------------------------------------ #
    #  Отправка рассылки
    # ------------------------------------------------------------------ #

    async def upload_attachment(
        self,
        current_user: UserModel,
        group_id: int,
        file: UploadFile,
    ) -> dict:
        await self._ensure_can_send(current_user, group_id)
        staging_chat_id, _ = await self._get_staging_chat(current_user, group_id)

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
            / str(staging_chat_id)
            / now.strftime("%Y")
            / now.strftime("%m")
            / f"{uuid.uuid4().hex}{suffix.lower()}"
        )
        storage_path = get_settings().STORAGE_DIRECTORY / storage_key
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(storage_path, "wb") as out_file:
            await out_file.write(file_content)

        attachment = await self.attachment_dao.add(
            chat_id=staging_chat_id,
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

        return ChatService._serialize_attachment(attachment)

    async def send_broadcast(
        self,
        current_user: UserModel,
        group_id: int,
        text: str | None,
        attachment_ids: list[int] | None = None,
    ) -> dict:
        await self._ensure_can_send(current_user, group_id)

        normalized_text = (text or "").strip() or None
        attachment_ids = list(dict.fromkeys(attachment_ids or []))
        if not normalized_text and not attachment_ids:
            raise HTTPException(
                status_code=400,
                detail="Broadcast must contain text or at least one attachment",
            )

        group = await self._get_group_or_404(group_id)
        member_ids = await self.broadcast_dao.get_member_user_ids(group_id)

        if not member_ids:
            raise HTTPException(status_code=400, detail="Broadcast group has no members")

        recipient_ids = sorted(uid for uid in member_ids if uid != current_user.id)
        if not recipient_ids:
            raise HTTPException(status_code=400, detail="No recipients to send broadcast to")

        pending_attachments = []
        staging_chat_id = None
        if attachment_ids:
            staging_chat_id, _ = await self._get_staging_chat(current_user, group_id)
            pending_attachments = await self.attachment_dao.get_pending_by_ids_for_sender(
                chat_id=staging_chat_id,
                uploader_id=current_user.id,
                attachment_ids=attachment_ids,
            )
            if len(pending_attachments) != len(attachment_ids):
                raise HTTPException(
                    status_code=400,
                    detail="Some attachments are invalid or already attached",
                )

        sent_count = 0
        for recipient_id in recipient_ids:
            chat = await self.chat_dao.get_or_create(current_user.id, recipient_id)
            message = await self.message_dao.add(
                chat_id=chat.id,
                sender_id=current_user.id,
                text=normalized_text,
            )

            if attachment_ids:
                if chat.id == staging_chat_id:
                    await self.attachment_dao.assign_to_message(attachment_ids, message.id)
                    for attachment in pending_attachments:
                        attachment.message_id = message.id
                    message.attachments = pending_attachments
                else:
                    copied_attachments = await self.attachment_dao.bulk_add(
                        [
                            {
                                "chat_id": chat.id,
                                "message_id": message.id,
                                "uploader_id": current_user.id,
                                "type": attachment.type,
                                "mime_type": attachment.mime_type,
                                "original_name": attachment.original_name,
                                "storage_key": attachment.storage_key,
                                "size_bytes": attachment.size_bytes,
                                "width": attachment.width,
                                "height": attachment.height,
                            }
                            for attachment in pending_attachments
                        ]
                    )
                    message.attachments = copied_attachments
            else:
                message.attachments = []

            message.reads = []
            await redis_client.publish(
                f"chat:messages:{recipient_id}",
                json.dumps({
                    "type": "new_message",
                    "chat_id": chat.id,
                    "message_id": message.id,
                    "sender_id": current_user.id,
                }),
            )
            sent_count += 1

        # Уведомляем самого отправителя чтобы его список чатов обновился
        await redis_client.publish(
            f"chat:messages:{current_user.id}",
            json.dumps({"type": "broadcast_sent"}),
        )

        return {
            "sent": True,
            "group_id": group_id,
            "group_name": group.name,
            "recipients_count": sent_count,
        }

    # ------------------------------------------------------------------ #
    #  Внутренние методы
    # ------------------------------------------------------------------ #

    async def _ensure_can_send(self, current_user: UserModel, group_id: int) -> None:
        if _is_system_admin(current_user):
            return

        can_send = await self.broadcast_dao.user_can_send(current_user.id, group_id)
        if not can_send:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to send broadcasts to this group",
            )

    async def _get_staging_chat(self, current_user: UserModel, group_id: int) -> tuple[int, int]:
        member_ids = await self.broadcast_dao.get_member_user_ids(group_id)
        recipient_ids = sorted(uid for uid in member_ids if uid != current_user.id)
        if not recipient_ids:
            raise HTTPException(status_code=400, detail="No recipients to send broadcast to")

        first_recipient_id = recipient_ids[0]
        chat = await self.chat_dao.get_or_create(current_user.id, first_recipient_id)
        return chat.id, first_recipient_id

    def _require_admin(self, user: UserModel) -> None:
        if not _is_system_admin(user):
            raise HTTPException(
                status_code=403,
                detail="Only administrators can perform this action",
            )

    async def _get_group_or_404(self, group_id: int) -> BroadcastGroup:
        group = await self.broadcast_dao.get_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Broadcast group not found")
        return group

    async def _get_accessible_group(
        self, current_user: UserModel, group_id: int
    ) -> BroadcastGroup:
        group = await self._get_group_or_404(group_id)
        is_admin = _is_system_admin(current_user)
        if is_admin:
            return group

        can_send = await self.broadcast_dao.user_can_send(current_user.id, group_id)
        if not can_send:
            raise HTTPException(status_code=403, detail="Access denied")
        return group

    async def _ensure_users_exist(self, user_ids: list[int]) -> None:
        if not user_ids:
            return
        result = await self.session.execute(
            select(UserModel.id).where(UserModel.id.in_(user_ids))
        )
        found_ids = set(result.scalars().all())
        missing = [uid for uid in user_ids if uid not in found_ids]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Users not found: {', '.join(map(str, missing))}",
            )

    async def _ensure_role_exists(self, role_id: int) -> None:
        result = await self.session.execute(
            select(Role.id).where(Role.id == role_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Role not found")

    async def _load_members(self, group_id: int) -> list[BroadcastGroupMember]:
        from sqlalchemy.orm import selectinload
        stmt = (
            select(BroadcastGroupMember)
            .where(BroadcastGroupMember.group_id == group_id)
            .options(selectinload(BroadcastGroupMember.user))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _serialize_members(self, members: list[BroadcastGroupMember]) -> list[dict]:
        user_ids = [m.user_id for m in members]
        if not user_ids:
            return []

        users_info = await self._get_users_info(user_ids)

        return [
            {
                "id": m.id,
                "user_id": m.user_id,
                "user": users_info.get(m.user_id, {"id": m.user_id}),
                "added_by_user_id": m.added_by_user_id,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in members
        ]

    async def _get_users_info(self, user_ids: list[int]) -> dict[int, dict]:
        """Получает ФИО и должность пользователей через MySQL (Nitro)."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id.in_(user_ids))
        )
        pg_users = result.scalars().all()

        platonus_to_pg: dict[int, int] = {}
        users_map: dict[int, dict] = {}

        for u in pg_users:
            if u.platonus_id:
                platonus_to_pg[u.platonus_id] = u.id
            else:
                users_map[u.id] = {"id": u.id, "shortname": f"User #{u.id}", "post": None}

        if platonus_to_pg:
            tutor_dao = TutorDAO(self.session_nitro)
            tutor_rows = await tutor_dao.get_tutors_with_positions_by_ids(
                list(platonus_to_pg.keys())
            )
            for tutor, position in tutor_rows:
                pg_id = platonus_to_pg.get(tutor.TutorID)
                if pg_id is None:
                    continue
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
                    "post": position.NameRU if position else None,
                }

        for uid in user_ids:
            if uid not in users_map:
                users_map[uid] = {"id": uid, "shortname": f"User #{uid}", "post": None}

        return users_map

    @staticmethod
    def _serialize_group(group: BroadcastGroup) -> dict:
        return {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "created_by_user_id": group.created_by_user_id,
            "members_count": len(group.members),
            "allowed_roles": [
                {
                    "role_id": gr.role_id,
                    "name_ru": gr.role.name_ru if gr.role else None,
                    "name_kz": gr.role.name_kz if gr.role else None,
                }
                for gr in group.allowed_roles
            ],
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        }

    @staticmethod
    def _serialize_role(role: Role) -> dict:
        return {
            "id": role.id,
            "name_ru": role.name_ru,
            "name_kz": role.name_kz,
        }
