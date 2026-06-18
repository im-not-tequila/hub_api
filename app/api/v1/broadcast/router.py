from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user
from app.services.broadcast import BroadcastService
from app.db.session import get_nitro_session, get_postgres_session
from app.api.v1.chat.schemas import ChatAttachmentResponse

from .schemas import (
    BroadcastGroupResponse,
    BroadcastGroupMemberResponse,
    BroadcastRoleResponse,
    BroadcastMeResponse,
    CreateBroadcastGroupRequest,
    UpdateBroadcastGroupRequest,
    AddBroadcastMembersRequest,
    AddBroadcastRoleRequest,
    SendBroadcastRequest,
    SendBroadcastResponse,
    DeletedResponse,
    RemovedResponse,
)

router = APIRouter()


def _get_broadcast_service(
    session_postgres: AsyncSession = Depends(get_postgres_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
) -> BroadcastService:
    return BroadcastService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    )


# ------------------------------------------------------------------ #
#  Информация о правах текущего пользователя
# ------------------------------------------------------------------ #

@router.get("/me", response_model=BroadcastMeResponse)
async def get_broadcast_me(
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """
    Возвращает права текущего пользователя в системе рассылок
    и список доступных ему групп.
    """
    from app.services.broadcast import _is_system_admin
    is_admin = _is_system_admin(current_user)
    groups = await service.get_groups(current_user)
    return {"is_admin": is_admin, "groups": groups}


# ------------------------------------------------------------------ #
#  Все доступные роли (для администраторов)
# ------------------------------------------------------------------ #

@router.get("/roles", response_model=List[BroadcastRoleResponse])
async def get_all_roles(
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Список всех активных ролей системы. Только для администраторов."""
    service._require_admin(current_user)
    roles = await service.get_all_roles()
    return [service._serialize_role(role) for role in roles]


# ------------------------------------------------------------------ #
#  Группы
# ------------------------------------------------------------------ #

@router.get("/groups", response_model=List[BroadcastGroupResponse])
async def get_broadcast_groups(
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """
    Список групп рассылки.
    Администратор видит все группы.
    Обычный пользователь — только группы, к которым у его роли есть доступ.
    """
    return await service.get_groups(current_user)


@router.post("/groups", response_model=BroadcastGroupResponse, status_code=201)
async def create_broadcast_group(
    body: CreateBroadcastGroupRequest,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Создать группу рассылки. Только для администраторов."""
    return await service.create_group(
        current_user,
        name=body.name,
        description=body.description,
        member_ids=body.member_ids,
    )


@router.get("/groups/{group_id}", response_model=BroadcastGroupResponse)
async def get_broadcast_group(
    group_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Получить группу рассылки по ID."""
    return await service.get_group(current_user, group_id)


@router.patch("/groups/{group_id}", response_model=BroadcastGroupResponse)
async def update_broadcast_group(
    group_id: int,
    body: UpdateBroadcastGroupRequest,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Обновить группу рассылки. Только для администраторов."""
    return await service.update_group(
        current_user,
        group_id,
        name=body.name,
        description=body.description,
    )


@router.delete("/groups/{group_id}", response_model=DeletedResponse)
async def delete_broadcast_group(
    group_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Удалить группу рассылки. Только для администраторов."""
    return await service.delete_group(current_user, group_id)


# ------------------------------------------------------------------ #
#  Участники группы
# ------------------------------------------------------------------ #

@router.get("/groups/{group_id}/members", response_model=List[BroadcastGroupMemberResponse])
async def get_broadcast_group_members(
    group_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Список участников группы рассылки."""
    return await service.get_members(current_user, group_id)


@router.post("/groups/{group_id}/members", response_model=List[BroadcastGroupMemberResponse])
async def add_broadcast_group_members(
    group_id: int,
    body: AddBroadcastMembersRequest,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Добавить участников в группу рассылки. Только для администраторов."""
    return await service.add_members(current_user, group_id, body.user_ids)


@router.delete("/groups/{group_id}/members/{user_id}", response_model=RemovedResponse)
async def remove_broadcast_group_member(
    group_id: int,
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Удалить участника из группы рассылки. Только для администраторов."""
    return await service.remove_member(current_user, group_id, user_id)


# ------------------------------------------------------------------ #
#  Роли с доступом к группе
# ------------------------------------------------------------------ #

@router.get("/groups/{group_id}/roles", response_model=List[BroadcastRoleResponse])
async def get_broadcast_group_roles(
    group_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Список ролей, имеющих доступ к рассылке в данную группу. Только для администраторов."""
    return await service.get_allowed_roles(current_user, group_id)


@router.post("/groups/{group_id}/roles", response_model=BroadcastRoleResponse, status_code=201)
async def add_broadcast_group_role(
    group_id: int,
    body: AddBroadcastRoleRequest,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Выдать роли доступ к рассылке через данную группу. Только для администраторов."""
    return await service.add_allowed_role(current_user, group_id, body.role_id)


@router.delete("/groups/{group_id}/roles/{role_id}", response_model=RemovedResponse)
async def remove_broadcast_group_role(
    group_id: int,
    role_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Отозвать доступ роли к рассылке через данную группу. Только для администраторов."""
    return await service.remove_allowed_role(current_user, group_id, role_id)


# ------------------------------------------------------------------ #
#  Отправка рассылки
# ------------------------------------------------------------------ #

@router.post("/groups/{group_id}/attachments", response_model=ChatAttachmentResponse, status_code=201)
async def upload_broadcast_attachment(
    group_id: int,
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """Загрузить вложение для последующей рассылки в группу."""
    return await service.upload_attachment(current_user, group_id, file)


@router.post("/groups/{group_id}/send", response_model=SendBroadcastResponse)
async def send_broadcast(
    group_id: int,
    body: SendBroadcastRequest,
    current_user: UserModel = Depends(get_current_user),
    service: BroadcastService = Depends(_get_broadcast_service),
):
    """
    Отправить рассылку всем участникам группы.
    Доступно администраторам и пользователям с разрешённой ролью для данной группы.
    Сообщение отправляется от имени текущего пользователя через личные чаты.
    """
    return await service.send_broadcast(
        current_user,
        group_id,
        body.text,
        attachment_ids=body.attachment_ids,
    )
