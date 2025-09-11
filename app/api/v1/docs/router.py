from fastapi import APIRouter, Depends

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user
from .schemas import DocumentResponse


router = APIRouter()


@router.get("/outgoing", response_model=DocumentResponse)
async def get_outgoing(current_user: UserModel = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.
    """

    result_user = User(id=current_user.id)

    return result_user
