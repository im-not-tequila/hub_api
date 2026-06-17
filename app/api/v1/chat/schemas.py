from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal


class ChatUserResponse(BaseModel):
    id: int
    firstname: str
    lastname: str
    shortname: str
    is_online: bool = False
    last_seen: Optional[str] = None
    post: Optional[str] = None

    class Config:
        from_attributes = True


class ChatAttachmentResponse(BaseModel):
    id: int
    chat_id: int
    message_id: Optional[int] = None
    uploader_id: int
    type: Literal["image", "file"]
    mime_type: str
    original_name: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    url: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: Optional[str] = None
    is_read: bool
    is_forwarded: bool = False
    forwarded_from_message_id: Optional[int] = None
    original_message_id: Optional[int] = None
    original_sender_id: Optional[int] = None
    created_at: Optional[str] = None
    attachments: list[ChatAttachmentResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ChatParticipantResponse(BaseModel):
    user: ChatUserResponse
    role: Literal["admin", "member"]
    is_active: bool
    added_by_user_id: Optional[int] = None
    removed_by_user_id: Optional[int] = None
    removed_at: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    id: int
    type: Literal["direct", "group"] = "direct"
    title: Optional[str] = None
    avatar_url: Optional[str] = None
    creator_user_id: Optional[int] = None
    participant: Optional[ChatUserResponse] = None
    participants: list[ChatParticipantResponse] = Field(default_factory=list)
    my_role: Optional[Literal["admin", "member"]] = None
    last_message: Optional[ChatMessageResponse] = None
    unread_count: int = 0

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    text: Optional[str] = None
    attachment_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload(self):
        normalized_text = (self.text or "").strip()
        if not normalized_text and not self.attachment_ids:
            raise ValueError("Message must contain text or at least one attachment")
        return self.model_copy(update={"text": normalized_text or None})


class ForwardMessageRequest(BaseModel):
    target_chat_id: Optional[int] = None
    recipient_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_payload(self):
        has_target_chat = self.target_chat_id is not None
        has_recipient = self.recipient_id is not None
        if has_target_chat == has_recipient:
            raise ValueError("Provide exactly one of target_chat_id or recipient_id")
        return self


class CreateChatRequest(BaseModel):
    participant_id: int


class CreateGroupChatRequest(BaseModel):
    title: str
    participant_ids: list[int] = Field(default_factory=list)
    avatar_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_payload(self):
        title = self.title.strip()
        if not title:
            raise ValueError("Group chat title is required")
        participant_ids = list(dict.fromkeys(self.participant_ids))
        return self.model_copy(update={"title": title, "participant_ids": participant_ids})


class UpdateGroupChatRequest(BaseModel):
    title: Optional[str] = None
    avatar_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_payload(self):
        title = self.title.strip() if self.title is not None else None
        if self.title is not None and not title:
            raise ValueError("Group chat title cannot be empty")
        return self.model_copy(update={"title": title})


class AddChatParticipantsRequest(BaseModel):
    user_ids: list[int]
    role: Literal["admin", "member"] = "member"

    @model_validator(mode="after")
    def validate_payload(self):
        user_ids = list(dict.fromkeys(self.user_ids))
        if not user_ids:
            raise ValueError("At least one user id is required")
        return self.model_copy(update={"user_ids": user_ids})


class UpdateChatParticipantRequest(BaseModel):
    role: Literal["admin", "member"]


class MarkAsReadResponse(BaseModel):
    marked_count: int


class UploadChatAttachmentResponse(ChatAttachmentResponse):
    pass
