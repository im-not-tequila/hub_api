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
    created_at: Optional[str] = None
    attachments: list[ChatAttachmentResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    id: int
    participant: Optional[ChatUserResponse] = None
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


class CreateChatRequest(BaseModel):
    participant_id: int


class MarkAsReadResponse(BaseModel):
    marked_count: int


class UploadChatAttachmentResponse(ChatAttachmentResponse):
    pass
