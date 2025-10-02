from pydantic import BaseModel
from typing import Optional

from app.schemas import UserResponse


class MeResponse(BaseModel):
    user: UserResponse

class TutorWithPosition(BaseModel):
    tutor_id: int
    lastname: Optional[str]
    firstname: Optional[str]
    patronymic: Optional[str]
    position_name: Optional[str]

    class Config:
        from_attributes = True

