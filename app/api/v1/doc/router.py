import json

from fastapi import APIRouter, Depends, Response, UploadFile, File, status, Query, Form, HTTPException
from fastapi.responses import FileResponse

from typing import List

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user
from app.schemas import (DocumentUploadRequest, OutgoingResponse, DocumentTypesAndCategory, DocumentSignRequest, SampleDocument)
from app.services.document import DocumentService


router = APIRouter()


@router.get(
    path="/incoming",
    response_model=List[OutgoingResponse]
)
async def incoming(
        current_user: UserModel = Depends(get_current_user)
) -> List[OutgoingResponse]:
    return await DocumentService().incoming(current_user)


@router.get(
    path="/outgoing",
    response_model=List[OutgoingResponse]
)
async def outgoing(
        current_user: UserModel = Depends(get_current_user)
) -> List[OutgoingResponse]:
    return await DocumentService().outgoing(current_user)


@router.get(
    path="/pending-execution",
    response_model=List[OutgoingResponse]
)
async def pending_execution(
        current_user: UserModel = Depends(get_current_user)
) -> List[OutgoingResponse]:
    return await DocumentService().pending_execution(current_user)


@router.get(
    path="/executed",
    response_model=List[OutgoingResponse]
)
async def executed(
        current_user: UserModel = Depends(get_current_user)
) -> List[OutgoingResponse]:
    return await DocumentService().executed(current_user)


@router.get(
    path="/types-and-categories",
    response_model=List[DocumentTypesAndCategory]
)
async def types_and_categories(
        lang: str = Query('ru', description="Язык: ru, kz, en"),
        current_user: UserModel = Depends(get_current_user)
):
    return await DocumentService().types_and_categories(current_user, lang)


@router.post(
    path="/upload",
    status_code=status.HTTP_204_NO_CONTENT
)
async def upload(
    document_name: str = Form(...),
    document_type_id: int = Form(...),
    recipient_id: int = Form(...),
    approver_user_ids: str = Form(...),  # приходит как JSON-строка
    signature: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
):
    approver_user_ids_list = json.loads(approver_user_ids)

    data = DocumentUploadRequest(
        document_name=document_name,
        document_type_id=document_type_id,
        recipient_id=recipient_id,
        approver_user_ids=approver_user_ids_list,
        signature=signature
    )

    await DocumentService().upload(data, file, current_user)

@router.post(
    path="/upload-custom/{document_type}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def upload_custom():
    pass

@router.post(
    path="/{document_id}/sign",
    status_code=status.HTTP_204_NO_CONTENT
)
async def sign(
        document_id: int,
        data: DocumentSignRequest,
        current_user: UserModel = Depends(get_current_user)
):
    await DocumentService().sign(
        document_id=document_id,
        user_signature=data.signature,
        user=current_user,
        resolution=data.resolution,
        executors=data.executors
    )


@router.post(
    path="/{document_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT
)
async def cancel(
        document_id: int,
        current_user: UserModel = Depends(get_current_user)
):
    await DocumentService().cancel(
        document_id=document_id,
        approver_id=current_user.id
    )


@router.post(
    path="/{document_id}/execute",
    status_code=status.HTTP_204_NO_CONTENT
)
async def execute(
        document_id: int,
        current_user: UserModel = Depends(get_current_user)
):
    await DocumentService().execute(
        document_id=document_id,
        executor_id=current_user.id
    )


@router.post(
    path="/{document_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT
)
async def revoke(
        document_id: int,
        current_user: UserModel = Depends(get_current_user)
):
    await DocumentService().revoke(
        user_id=current_user.id,
        document_id=document_id
    )


@router.post(
    path="/{document_id}/hide",
    status_code=status.HTTP_204_NO_CONTENT
)
async def hide(
        document_id: int,
        current_user: UserModel = Depends(get_current_user)
):
    await DocumentService().hide(
        user_id=current_user.id,
        document_id=document_id
    )

@router.post(
    path="/{document_id}/unhide",
    status_code=status.HTTP_204_NO_CONTENT
)
async def unhide(
        document_id: int,
        current_user: UserModel = Depends(get_current_user)
):
    await DocumentService().unhide(
        user_id=current_user.id,
        document_id=document_id
    )


@router.get(
    path="/{document_id}/pdf"
)
async def pdf(
        document_id: int,
        current_user: UserModel = Depends(get_current_user)
):
    file_path = await DocumentService().pdf(document_id)

    return FileResponse(file_path, media_type="application/pdf", filename="document.pdf")


@router.get(
    path="/samples",
    response_model=List[SampleDocument]
)
async def samples(
        lang: str = Query('ru', description="Язык: ru, kz, en"),
        current_user: UserModel = Depends(get_current_user)
):
    return await DocumentService().samples()


@router.get(
    path="/sample/{sample_document_id}/pdf",
    response_model=List[SampleDocument]
)
async def sample_pdf(
        sample_document_id: int,
        current_user: UserModel = Depends(get_current_user)
):
    return await DocumentService().sample_pdf(sample_document_id)


@router.get(
    path="/sample/{sample_document_id}/download",
    response_model=List[SampleDocument],
    summary="Скачать шаблон DOCX",
)
async def sample_pdf(
        sample_document_id: int,
        current_user: UserModel = Depends(get_current_user)
):
    print('111111111111111111111')
    return await DocumentService().sample_download(sample_document_id)
