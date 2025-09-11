from pydantic import BaseModel

from app.schemas_internal import User


class MeResponse(BaseModel):
    user: User
