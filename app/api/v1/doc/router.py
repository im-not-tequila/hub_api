import json
import asyncio

from fastapi import APIRouter, Depends, Response, UploadFile, File, status, Query, Form
from fastapi.responses import FileResponse

from typing import List

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user
from app.schemas import DocumentUploadRequest, OutgoingResponse, DocumentTypesAndCategory, DocumentSignRequest, DocumentExecuteRequest, DocumentCancelRequest
from app.services.document import DocumentService


router = APIRouter()


@router.get(
    path="/incoming",
    response_model=List[OutgoingResponse]
)
async def incoming(
        current_user: UserModel = Depends(get_current_user)
) -> List[OutgoingResponse]:
    return await DocumentService().collect_user_documents(current_user, 'incoming')


@router.get(
    path="/outgoing",
    response_model=List[OutgoingResponse]
)
async def outgoing(
        current_user: UserModel = Depends(get_current_user)
) -> List[OutgoingResponse]:
    # await asyncio.sleep(15)
    return await DocumentService().collect_user_documents(current_user, 'outgoing')


@router.get(
    path="/pending_execution",
    response_model=List[OutgoingResponse]
)
async def pending_execution(
        current_user: UserModel = Depends(get_current_user)
) -> List[OutgoingResponse]:
    return await DocumentService().collect_user_documents(current_user, 'pending_execution')


@router.get(
    path="/executed",
    response_model=List[OutgoingResponse]
)
async def executed(
        current_user: UserModel = Depends(get_current_user)
) -> List[OutgoingResponse]:
    return await DocumentService().collect_user_documents(current_user, 'executed')


@router.get(
    path="/types_and_categories",
    response_model=List[DocumentTypesAndCategory]
)
async def types_and_categories(
        lang: str = Query('ru', description="Язык: ru, kz, en"),
        current_user: UserModel = Depends(get_current_user)
):
    return await DocumentService().types_and_categories(current_user, lang)


@router.post(
    path="/upload"
)
async def upload(
    document_name: str = Form(...),
    document_type_id: int = Form(...),
    recipient_id: int = Form(...),
    approver_user_ids: str = Form(...),  # приходит как JSON-строка
    cms: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
):
    try:
        approver_user_ids_list = json.loads(approver_user_ids)
    except json.JSONDecodeError:
        return Response(content="Invalid JSON for approver_user_ids", status_code=status.HTTP_400_BAD_REQUEST)

    data = DocumentUploadRequest(
        document_name=document_name,
        document_type_id=document_type_id,
        recipient_id=recipient_id,
        approver_user_ids=approver_user_ids_list,
        cms=cms
    )

    await DocumentService().upload(data, file, current_user)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    path="/sign",
)
async def sign(
        data: DocumentSignRequest,
        current_user: UserModel = Depends(get_current_user)
):
    await DocumentService().sign(
        document_id=data.document_id,
        user_signature=data.cms,
        user=current_user,
        resolution=data.resolution,
        executors=data.executors
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    path="/cancel"
)
async def cancel(
        data: DocumentCancelRequest,
        current_user: UserModel = Depends(get_current_user)
):
    await DocumentService().cancel(
        document_id=data.document_id,
        approver_id=current_user.id
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    path="/execute",
)
async def execute(
        data: DocumentExecuteRequest,
        current_user: UserModel = Depends(get_current_user)
):
    await DocumentService().execute(
        document_id=data.document_id,
        executor_id=current_user.id
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    path="/pdf"
)
async def pdf(
        document_id: int = Query(...),
        current_user: UserModel = Depends(get_current_user)
):
    file_path = await DocumentService().pdf(document_id)

    return FileResponse(file_path, media_type="application/pdf", filename="document.pdf")
