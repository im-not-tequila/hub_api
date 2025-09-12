from pydantic import BaseModel, Field
from typing import Optional


class User(BaseModel):
    id: int
    firstname: str
    lastname: str
    patronymic: Optional[str] = None
    shortname: str = Field(default="")

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
