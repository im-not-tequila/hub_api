from enum import Enum
from typing import List, Optional
from datetime import date

from pydantic import BaseModel, Field, HttpUrl


class DocumentUploadRequest(BaseModel):
    document_name: str
    document_type_id: int
    recipient_id: int
    approver_user_ids: List[int]
    cms: str


class DocumentStatus(str, Enum):
    SIGNED = 'Утвержден'
    REJECTED = 'Отклонен'
    PENDING = 'На согласовании'


class Person(BaseModel):
    name: str
    role: Optional[str] = None
    avatar: Optional[HttpUrl] = None
    status: Optional[DocumentStatus] = None


class AgreementItem(Person):
    """Если структура соглашения полностью совпадает с Person, можно унаследовать."""
    pass


class DocumentResponse(BaseModel):
    id: int
    name: str
    sender: Person
    recipient: Person
    agreement: List[AgreementItem] = Field(default_factory=list)
    date: date
    status: DocumentStatus

    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "name": "Акт приема-передачи",
                "sender": {
                    "name": "Иванов Иван",
                    "role": "Менеджер",
                    "avatar": "https://example.com/avatars/user-17.jpg"
                },
                "recipient": {
                    "name": "Петров Пётр",
                    "role": "Юрист",
                    "avatar": "https://example.com/avatars/user-18.jpg",
                    "status": "На согласовании"
                },
                "agreement": [
                    {
                        "name": "Семенов С.",
                        "role": "Фин. отдел",
                        "avatar": "https://example.com/avatars/user-22.jpg",
                        "status": "Подписано"
                    },
                    {
                        "name": "Сидорова А.",
                        "role": "Бухгалтер",
                        "avatar": "https://example.com/avatars/user-23.jpg",
                        "status": "На согласовании"
                    }
                ],
                "date": "2025-09-01",
                "status": "На согласовании"
            }
        }
