import re

from pydantic import BaseModel, Field, field_validator

from typing import Optional


class UserEcpInfo(BaseModel):
    firstname: str = Field(alias='common_name')
    lastname: str = Field(alias='surname')
    patronymic: Optional[str] = Field(default=None, alias='given_name')
    iin_number: str = Field(alias='serial_number')
    bin_number: Optional[str] = Field(default=None, alias='ou')

    class Config:
        populate_by_name = True

    @field_validator('firstname', mode='before')
    def extract_name_from_common_name(cls, value):
        try:
            return value.split(' ')[1]
        except IndexError:
            return value

    @field_validator('iin_number', 'bin_number', mode='before')
    def extract_digits_from_fields(cls, value):
        """Валидатор для извлечения только цифр из IIN и BIN"""

        if value is None:
            return value

        match = re.search(r'\d+', value)

        return match.group() if match else value
