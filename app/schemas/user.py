import datetime

from pydantic import BaseModel, Field
from typing import Optional


class UserResponse(BaseModel):
    id: int
    firstname: str
    lastname: str
    structural_subdivision: str
    subdivision_id: int
    patronymic: Optional[str] = None
    shortname: str = Field(default="")
    post: str = Field(default="")

    def model_post_init(self, __context) -> None:
        """Форматируем строковые поля и автоматически формируем shortname"""

        # Приводим фамилию, имя, отчество в формат "Первая буква заглавная, остальные строчные"
        if self.firstname:
            self.firstname = self.firstname.strip().capitalize()
        if self.lastname:
            self.lastname = self.lastname.strip().capitalize()
        if self.patronymic:
            self.patronymic = self.patronymic.strip().capitalize()

        # --- ДОБАВЛЕНО: Нормализация должности ---
        if self.post:
            self.post = self.post.strip().capitalize()
        # ----------------------------------------

        # Формируем инициалы
        first_initial = f"{self.firstname[0].upper()}." if self.firstname else ""
        patronymic_initial = f" {self.patronymic[0].upper()}." if self.patronymic else ""

        # Генерируем shortname
        self.shortname = f"{self.lastname} {first_initial}{patronymic_initial}".strip()

    class Config:
        from_attributes = True

class BarrierResponse(BaseModel):
    id: int
    inout_data: str
    access_type: str
    building_name: str
    address: str
    time: str  # строка вида "HH:MM"

    class Config:
        from_attributes = True


class WorkingHoursResponse(BaseModel):
    id: int
    date: datetime.date
    working_hours: float


class NotificationResponse(BaseModel):
    id: int
    sender_user_id: int
    sender_name: str
    title: str
    message: str
    is_read: bool
    other_data: dict | None
    created_at: datetime.datetime
