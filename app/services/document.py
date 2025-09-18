import aiofiles

from datetime import datetime

from fastapi import HTTPException, UploadFile

from app.services.ncanode import NCANode
from app.core.settings import get_settings
from app.db.session import get_postgres_session
from app.dao.postgres import DocumentDAO, ApproverDAO
from app.services.sigex import Sigex
from app.schemas.document import DocumentUploadRequest
from app.models.postgres import User as UserModel


class DocumentService:
    async def upload(self, data: DocumentUploadRequest, file: UploadFile, current_user: UserModel):
        user_ecp_info = NCANode().cms_verify(data.signed_data, data.original_data)

        if not user_ecp_info:
            raise HTTPException(status_code=400, detail="Invalid signature")

        async with get_postgres_session() as postgres_session:
            document = await DocumentDAO(postgres_session).add(
                author_id=current_user.id,
                recipient_id=data.recipient_id,
                document_type_id=data.document_type_id,
                name=data.document_name,
            )

            sigex_document_name = document.document_type

        sigex_data = await Sigex.send_to_sigex(
            document_name=sigex_document_name,
            cms=data.cms,
            file_bytes=await file.read()
        )

        settings = get_settings()
        document_directory = settings.STORAGE_DIRECTORY / "documents" / datetime.now().strftime("%Y") / str(document.id)
        document_directory.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(document_directory / f"Base64-{current_user.id}.cms", "w") as f:
            await f.write(data.cms)

        async with aiofiles.open(document_directory / f"Sigex-Base64-{current_user.id}.cms", "w") as f:
            await f.write(sigex_data['sigex_cms'])

        async with aiofiles.open(document_directory / 'original.pdf', "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # читаем по 1 МБ
                await out_file.write(chunk)

        async with get_postgres_session() as postgres_session:
            await DocumentDAO(postgres_session).update(
                obj_id=document.id,
                sigex_id=sigex_data['sigex_document_id'],
            )

            approvers_data = [
                {"document_id": document.id, "approver_user_id": user_id}
                for user_id in data.approver_user_ids
            ]

            await ApproverDAO(postgres_session).bulk_add(approvers_data)
