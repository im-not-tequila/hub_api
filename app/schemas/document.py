from enum import Enum
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class DocumentUploadRequest(BaseModel):
    document_name: str
    document_type_id: int
    recipient_id: int
    approver_user_ids: List[int]
    cms: str


class DocumentStatus(str, Enum):
    PENDING = "pending"
    SIGNED = "signed"
    REJECTED = "cancelled"

    NOT_APPROVED_BY_YOU = 'Вы не согласовали'
    APPROVED_BY_YOU = 'Вы согласовали'
    NOT_SIGNED_BY_YOU = 'Вы не подписали'
    SIGNED_BY_YOU = 'Вы подписали'
    REJECTED_BY_YOU = 'Вы отклонили'
    NOT_EXECUTED_BY_YOU = 'Вы не исполнили'
    EXECUTED_BY_YOU = 'Вы исполнили'


class Person(BaseModel):
    id: int
    firstname: str
    lastname: str
    patronymic: Optional[str] = None
    shortname: str = Field(default="")
    role: Optional[str] = None
    avatar: Optional[HttpUrl] = None
    status: Optional[DocumentStatus] = None

    def model_post_init(self, __context) -> None:
        """Форматируем строковые поля и автоматически формируем shortname"""

        # Приводим фамилию, имя, отчество в формат "Первая буква заглавная, остальные строчные"
        if self.firstname:
            self.firstname = self.firstname.strip().capitalize()
        if self.lastname:
            self.lastname = self.lastname.strip().capitalize()
        if self.patronymic:
            self.patronymic = self.patronymic.strip().capitalize()

        # Формируем инициалы
        first_initial = f"{self.firstname[0].upper()}." if self.firstname else ""
        patronymic_initial = f" {self.patronymic[0].upper()}." if self.patronymic else ""

        # Генерируем shortname
        self.shortname = f"{self.lastname} {first_initial}{patronymic_initial}".strip()


class ApproverPerson(Person):
    """Если структура соглашения полностью совпадает с Person, можно унаследовать."""
    pass


class OutgoingResponse(BaseModel):
    id: int
    name: str
    sender: Person
    recipient: Person
    approvers: List[ApproverPerson] = Field(default_factory=list)
    type: str
    type_id: int
    create_datetime: datetime
    status: DocumentStatus

    class Config:
        json_schema_extra = {
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


class IncomingResponse(OutgoingResponse):
    pass


class DocumentType(BaseModel):
    id: int
    name: str


class DocumentCategory(DocumentType):
    pass


class DocumentTypesAndCategory(BaseModel):
    category: DocumentCategory
    document_types: List[DocumentType] = Field(default_factory=list)


class DocumentSignRequest(BaseModel):
    document_id: int
    resolution: str | None
    executors: List[int]
    cms: str


class DocumentExecuteRequest(BaseModel):
    document_id: int


class DocumentCancelRequest(BaseModel):
    document_id: int

