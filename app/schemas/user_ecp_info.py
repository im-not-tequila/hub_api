from pydantic import BaseModel, Field, field_validator
from typing import Optional


class UserEcpInfo(BaseModel):
    firstname: str = Field(alias='commonName')
    lastname: str = Field(alias='surName')
    patronymic: Optional[str] = Field(default=None, alias='dn')
    shortname: str = Field(default="")
    iin_number: str = Field(alias='iin')
    bin_number: Optional[str] = Field(default=None, alias='bin')  # <-- Исправлено

    class Config:
        populate_by_name = True

    @field_validator('firstname', mode='before')
    def extract_firstname(cls, value: str) -> str:
        """Берем имя из поля commonName (второе слово)."""
        if not value:
            return value
        parts = value.split(' ')
        return parts[1] if len(parts) > 1 else parts[0]

    @field_validator('patronymic', mode='before')
    def extract_patronymic(cls, value: Optional[str]) -> Optional[str]:
        """
        Ищем GIVENNAME в DN. Если нет, возвращаем None.
        Пример DN:
        GIVENNAME=ВЛАДИМИРОВИЧ, C=KZ, SERIALNUMBER=IIN001116550151, SURNAME=СВИРИДОВ, CN=СВИРИДОВ ВЛАДИСЛАВ
        """
        if not value or 'GIVENNAME=' not in value:
            return None

        try:
            return value.split('GIVENNAME=')[1].split(',')[0].strip()
        except IndexError:
            return None
