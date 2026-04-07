import json
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, status, Query, Form, HTTPException
from fastapi.responses import FileResponse

from typing import List

from sqlalchemy import select

from app.core.settings import get_settings
from app.models.postgres import (
    User as UserModel,
    NormativeDocumentCategory as NormativeDocumentCategoryModel,
    NormativeDocumentSubcategory as NormativeDocumentSubcategoryModel,
    NormativeDocument as NormativeDocumentModel,
)
from app.api.v1.auth.deps import get_current_user
from app.schemas import (
    DocumentUploadRequest,
    OutgoingResponse,
    DocumentTypesAndCategory,
    DocumentSignRequest,
    SampleDocument,
    NormativeDocumentCategory,
    NormativeDocumentSubcategory,
    NormativeDocumentItem,
)
from app.services.document import DocumentService
from app.db.session import get_nitro_session, get_postgres_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


def _resolve_multilang_name(obj, lang: str) -> str:
    if lang == "kz":
        return obj.name_kz
    if lang == "en":
        return obj.name_en
    return obj.name_ru


def _resolve_normative_document_file(document_id: int) -> Path:
    base_dir = get_settings().STORAGE_DIRECTORY / "norm_docs"

    for path in base_dir.rglob(f"{document_id}.*"):
        if path.is_file():
            return path

    raise HTTPException(status_code=404, detail="Normative document file not found")


@router.get(
    path="/incoming",
    response_model=List[OutgoingResponse]
)
async def incoming(
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
) -> List[OutgoingResponse]:
    return await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).incoming(current_user)


@router.get(
    path="/outgoing",
    response_model=List[OutgoingResponse]
)
async def outgoing(
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
) -> List[OutgoingResponse]:
    return await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).outgoing(current_user)


@router.get(
    path="/pending-execution",
    response_model=List[OutgoingResponse]
)
async def pending_execution(
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
) -> List[OutgoingResponse]:
    return await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).pending_execution(current_user)


@router.get(
    path="/executed",
    response_model=List[OutgoingResponse]
)
async def executed(
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
) -> List[OutgoingResponse]:
    return await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).executed(current_user)


@router.get(
    path="/types-and-categories",
    response_model=List[DocumentTypesAndCategory]
)
async def types_and_categories(
        lang: str = Query('ru', description="Язык: ru, kz, en"),
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    return await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).types_and_categories(current_user, lang)


@router.get(
    path="/normative/categories",
    response_model=List[NormativeDocumentCategory],
)
async def normative_categories(
        lang: str = Query("ru", description="Язык: ru, kz, en"),
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
):
    _ = current_user

    categories_result = await session_postgres.execute(
        select(NormativeDocumentCategoryModel)
        .where(NormativeDocumentCategoryModel.is_active.is_(True))
        .order_by(NormativeDocumentCategoryModel.id)
    )
    categories = categories_result.scalars().all()

    subcategories_result = await session_postgres.execute(
        select(NormativeDocumentSubcategoryModel)
        .where(NormativeDocumentSubcategoryModel.is_active.is_(True))
        .order_by(NormativeDocumentSubcategoryModel.id)
    )
    subcategories = subcategories_result.scalars().all()

    subcategories_by_category_id: dict[int, list[NormativeDocumentSubcategoryModel]] = {}
    for subcategory in subcategories:
        subcategories_by_category_id.setdefault(
            subcategory.normative_document_category_id,
            []
        ).append(subcategory)

    return [
        NormativeDocumentCategory(
            id=category.id,
            name=_resolve_multilang_name(category, lang),
            subcategories=[
                NormativeDocumentSubcategory(
                    id=subcategory.id,
                    name=_resolve_multilang_name(subcategory, lang),
                )
                for subcategory in subcategories_by_category_id.get(category.id, [])
            ],
        )
        for category in categories
    ]


@router.get(
    path="/normative/documents",
    response_model=List[NormativeDocumentItem],
)
async def normative_documents(
        lang: str = Query("ru", description="Язык: ru, kz, en"),
        category_id: int | None = Query(None, description="ID категории"),
        subcategory_id: int | None = Query(None, description="ID подкатегории"),
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
):
    _ = current_user

    query = (
        select(
            NormativeDocumentModel,
            NormativeDocumentSubcategoryModel.normative_document_category_id,
        )
        .join(
            NormativeDocumentSubcategoryModel,
            NormativeDocumentSubcategoryModel.id == NormativeDocumentModel.normative_document_subcategory_id,
        )
        .where(
            NormativeDocumentModel.is_active.is_(True),
            NormativeDocumentSubcategoryModel.is_active.is_(True),
        )
        .order_by(NormativeDocumentModel.id)
    )

    if category_id is not None:
        query = query.where(
            NormativeDocumentSubcategoryModel.normative_document_category_id == category_id
        )
    if subcategory_id is not None:
        query = query.where(
            NormativeDocumentModel.normative_document_subcategory_id == subcategory_id
        )

    rows = (await session_postgres.execute(query)).all()

    return [
        NormativeDocumentItem(
            id=document.id,
            name=_resolve_multilang_name(document, lang),
            subcategory_id=document.normative_document_subcategory_id,
            category_id=resolved_category_id,
        )
        for document, resolved_category_id in rows
    ]


@router.get(
    path="/normative/{document_id}/view",
)
async def view_normative_document(
        document_id: int,
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
):
    _ = current_user

    document = await session_postgres.scalar(
        select(NormativeDocumentModel).where(
            NormativeDocumentModel.id == document_id,
            NormativeDocumentModel.is_active.is_(True),
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Normative document not found")

    file_path = _resolve_normative_document_file(document_id)
    return FileResponse(path=file_path)


@router.get(
    path="/normative/{document_id}/download",
)
async def download_normative_document(
        document_id: int,
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
):
    _ = current_user

    document = await session_postgres.scalar(
        select(NormativeDocumentModel).where(
            NormativeDocumentModel.id == document_id,
            NormativeDocumentModel.is_active.is_(True),
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Normative document not found")

    file_path = _resolve_normative_document_file(document_id)
    download_filename = f"{document_id}{file_path.suffix}"
    media_type = mimetypes.guess_type(download_filename)[0] or "application/octet-stream"
    return FileResponse(
        path=file_path,
        filename=download_filename,
        media_type=media_type,
    )


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
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    approver_user_ids_list = json.loads(approver_user_ids)

    data = DocumentUploadRequest(
        document_name=document_name,
        document_type_id=document_type_id,
        recipient_id=recipient_id,
        approver_user_ids=approver_user_ids_list,
        signature=signature
    )

    await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).upload(data, file, current_user)

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
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).sign(
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
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).cancel(
        document_id=document_id,
        approver_id=current_user.id
    )


@router.post(
    path="/{document_id}/execute",
    status_code=status.HTTP_204_NO_CONTENT
)
async def execute(
        document_id: int,
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).execute(
        document_id=document_id,
        executor_id=current_user.id
    )


@router.post(
    path="/{document_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT
)
async def revoke(
        document_id: int,
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).revoke(
        user_id=current_user.id,
        document_id=document_id
    )


@router.post(
    path="/{document_id}/hide",
    status_code=status.HTTP_204_NO_CONTENT
)
async def hide(
        document_id: int,
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).hide(
        user_id=current_user.id,
        document_id=document_id
    )

@router.post(
    path="/{document_id}/unhide",
    status_code=status.HTTP_204_NO_CONTENT
)
async def unhide(
        document_id: int,
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).unhide(
        user_id=current_user.id,
        document_id=document_id
    )


@router.get(
    path="/{document_id}/pdf"
)
async def pdf(
        document_id: int,
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    file_path = await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).pdf(document_id)

    return FileResponse(file_path, media_type="application/pdf", filename="document.pdf")


@router.get(
    path="/samples",
    response_model=List[SampleDocument]
)
async def samples(
        lang: str = Query('ru', description="Язык: ru, kz, en"),
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    return await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).samples()


@router.get(
    path="/sample/{sample_document_id}/pdf",
    response_model=List[SampleDocument]
)
async def sample_pdf(
        sample_document_id: int,
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    return await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).sample_pdf(sample_document_id)


@router.get(
    path="/sample/{sample_document_id}/download",
    response_model=List[SampleDocument],
    summary="Скачать шаблон DOCX",
)
async def sample_download(
        sample_document_id: int,
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
):
    return await DocumentService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).sample_download(sample_document_id)
