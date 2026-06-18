from pydantic import BaseModel, Field, model_validator
from typing import Optional


# ------------------------------------------------------------------ #
#  Группы
# ------------------------------------------------------------------ #

class BroadcastAllowedRoleResponse(BaseModel):
    role_id: int
    name_ru: Optional[str] = None
    name_kz: Optional[str] = None

    class Config:
        from_attributes = True


class BroadcastGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_by_user_id: Optional[int] = None
    members_count: int = 0
    allowed_roles: list[BroadcastAllowedRoleResponse] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class CreateBroadcastGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None
    member_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload(self):
        name = self.name.strip()
        if not name:
            raise ValueError("Group name is required")
        member_ids = list(dict.fromkeys(self.member_ids))
        return self.model_copy(update={"name": name, "member_ids": member_ids})


class UpdateBroadcastGroupRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_payload(self):
        name = self.name.strip() if self.name is not None else None
        if self.name is not None and not name:
            raise ValueError("Group name cannot be empty")
        return self.model_copy(update={"name": name})


# ------------------------------------------------------------------ #
#  Участники
# ------------------------------------------------------------------ #

class BroadcastMemberUserInfo(BaseModel):
    id: int
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    shortname: Optional[str] = None
    post: Optional[str] = None

    class Config:
        from_attributes = True


class BroadcastGroupMemberResponse(BaseModel):
    id: int
    user_id: int
    user: Optional[BroadcastMemberUserInfo] = None
    added_by_user_id: Optional[int] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class AddBroadcastMembersRequest(BaseModel):
    user_ids: list[int]

    @model_validator(mode="after")
    def validate_payload(self):
        user_ids = list(dict.fromkeys(self.user_ids))
        if not user_ids:
            raise ValueError("At least one user_id is required")
        return self.model_copy(update={"user_ids": user_ids})


# ------------------------------------------------------------------ #
#  Роли
# ------------------------------------------------------------------ #

class BroadcastRoleResponse(BaseModel):
    id: int
    name_ru: str
    name_kz: str

    class Config:
        from_attributes = True


class AddBroadcastRoleRequest(BaseModel):
    role_id: int


# ------------------------------------------------------------------ #
#  Отправка рассылки
# ------------------------------------------------------------------ #

class SendBroadcastRequest(BaseModel):
    text: Optional[str] = None
    attachment_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload(self):
        normalized_text = (self.text or "").strip() or None
        attachment_ids = list(dict.fromkeys(self.attachment_ids))
        if not normalized_text and not attachment_ids:
            raise ValueError("Broadcast must contain text or at least one attachment")
        return self.model_copy(update={"text": normalized_text, "attachment_ids": attachment_ids})


class SendBroadcastResponse(BaseModel):
    sent: bool
    group_id: int
    group_name: str
    recipients_count: int


# ------------------------------------------------------------------ #
#  Общие ответы
# ------------------------------------------------------------------ #

class BroadcastMeResponse(BaseModel):
    is_admin: bool
    groups: list[BroadcastGroupResponse] = Field(default_factory=list)


class DeletedResponse(BaseModel):
    deleted: bool


class RemovedResponse(BaseModel):
    removed: bool
