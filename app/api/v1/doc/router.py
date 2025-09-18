from fastapi import APIRouter, Depends, Response, UploadFile, File, status

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user
from app.schemas.document import DocumentUploadRequest, DocumentResponse
from app.services.document import DocumentService


router = APIRouter()


@router.get("/outgoing", response_model=DocumentResponse)
async def get_outgoing(current_user: UserModel = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.
    """
    pass
    # result_user = User(id=current_user.id)
    #
    # return result_user


@router.post(path="/upload")
async def signed(
        data: DocumentUploadRequest,
        file: UploadFile = File(...),
        current_user: UserModel = Depends(get_current_user)
):
    print(data.model_dump())

    await DocumentService().upload(data, file, current_user)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


