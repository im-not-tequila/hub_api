from fastapi import APIRouter, Depends

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user
from app.schemas_internal import User


router = APIRouter()


@router.get("/me", response_model=User)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.
    """

    result_user = User(id=current_user.id)

    return result_user
