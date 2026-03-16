from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class ChatUserResponse(BaseModel):
    id: int
    firstname: str
    lastname: str
    shortname: str
    avatar: Optional[str] = None
    is_online: bool = False
    last_seen: Optional[str] = None
    post: Optional[str] = None

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str
    is_read: bool
    created_at: Optional[str] = None

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
    text: str


class CreateChatRequest(BaseModel):
    participant_id: int


class MarkAsReadResponse(BaseModel):
    marked_count: int
