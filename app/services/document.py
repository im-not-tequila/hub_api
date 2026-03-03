import aiofiles
import base64
import asyncio

from fastapi.responses import FileResponse
from fastapi import HTTPException, UploadFile

from datetime import datetime
from typing import List

from app.dao.mysql import TutorDAO, StudentDAO
from app.services.ncanode import NCANode
from app.services.notification import NotificationService
from app.core.settings import get_settings
from app.dao.postgres import DocumentDAO, ApproverDAO, ExecutorDAO, HiddenDocumentDAO, UserInfoDAO, SampleDocumentDAO
from app.services.sigex import Sigex

from app.schemas import (
    DocumentUploadRequest,
    DocumentTypesAndCategory,
    DocumentCategory,
    DocumentType,
    OutgoingResponse,
    Person,
    ApproverPerson,
    SampleDocument
)

from app.models.postgres import (
    User as UserModel,
    UserInfo as UserInfoModel,
    Approver as ApproverModel,
    Document as DocumentModel,
    Executor as ExecutorModel,
    DocumentStatus,
    ApproverStatus,
    ExecutorStatus,
    SampleDocument as SampleDocumentModel
)

from app.models.mysql.nitro import (
    Tutor as TutorModel,
    Student as StudentModel,
    StructuralSubdivision as StructuralSubdivisionModel,
    TutorPositions as TutorPositionsModel
)

from app.dao.migrate_user import MigrateUserMysqlToPostgres
from sqlalchemy.ext.asyncio import AsyncSession


class DocumentService:
    def __init__(self, session_nitro: AsyncSession, session_postgres: AsyncSession):
        self.session_nitro = session_nitro
        self.session_postgres = session_postgres

    async def _collect_tutor_and_subdivision_by_documents(self, documents: list[DocumentModel]):
        document_ids = []
        platonus_ids = []

        for document in documents:
            platonus_ids.append(document.recipient_user.platonus_id)
            document_ids.append(document.id)

        all_approvers = await ApproverDAO(self.session_postgres).get_all_filtered(
            filters={
                ApproverModel.document_id: document_ids,
            }
        )

        for approver in all_approvers:
            platonus_ids.append(approver.approver_user.platonus_id)

        platonus_ids = list(set(platonus_ids))

        tutors = await TutorDAO(self.session_nitro).join_structural_subdivision_and_tutor_positions(
            filters={
                TutorModel.TutorID: platonus_ids,
            },
            fields=[
                TutorModel.firstname,
                TutorModel.lastname,
                TutorModel.patronymic,
                StructuralSubdivisionModel.nameru,
                StructuralSubdivisionModel.namekz,
                StructuralSubdivisionModel.nameen,
                TutorPositionsModel.ID
            ]
        )

        tutors_dict = {}
        subdivision_dict = {}

        for _tutor, subdivision, position in tutors:
            tutors_dict[_tutor.TutorID] = _tutor
            subdivision_dict[_tutor.TutorID] = subdivision

        return tutors_dict, subdivision_dict

    async def _collect_sender_by_document(self, document: DocumentModel):
        if document.author_user.is_student:
            sender = await StudentDAO(self.session_nitro).get_by_id(document.author_user.platonus_id)
            sender_position = 'Студент'
        else:
            sender = await TutorDAO(self.session_nitro).get_one_or_none(
                fields=[TutorModel.firstname, TutorModel.lastname, TutorModel.patronymic],
                filters={
                    TutorModel.TutorID: document.author_user.platonus_id,
                }
            )
            sender_position = 'Сотрудник университета'

            all_tutors_and_position = await TutorDAO(self.session_nitro).join_structural_subdivision_and_tutor_positions(
                filters={
                    TutorModel.TutorID: document.author_user.platonus_id,
                },
                fields=[
                    TutorModel.TutorID,
                    StructuralSubdivisionModel.nameru,
                    StructuralSubdivisionModel.namekz,
                    StructuralSubdivisionModel.nameen,
                    TutorPositionsModel.ID,
                ]
            )

            for _tutor, _subdivision, _position in all_tutors_and_position:
                if _position:
                    sender_position = _subdivision.nameru

                break

        return {
            'platonus_user': sender,
            'hub_user': document.author_user,
            'position': sender_position,
            'status': DocumentStatus.SIGNED
        }

    async def _collect_recipient(self, document: DocumentModel, tutors_dict: dict, subdivision_dict: dict):
        recipient_approver = await ApproverDAO(self.session_postgres).get_one_or_none(
            filters={
                ApproverModel.document_id: document.id,
                ApproverModel.is_recipient: True,
                ApproverModel.approver_id: document.recipient_id,
            }
        )

        if recipient_approver is None:
            status = DocumentStatus.PENDING
        elif recipient_approver.status == ApproverStatus.REJECTED:
            status = DocumentStatus.REJECTED
        elif recipient_approver.status == ApproverStatus.SIGNED:
            status = DocumentStatus.SIGNED
        else:
            status = DocumentStatus.PENDING

        recipient_position = subdivision_dict.get(document.recipient_user.platonus_id)

        recipient = {
            'platonus_user': tutors_dict.get(document.recipient_user.platonus_id),
            'hub_user': document.recipient_user,
            'position': recipient_position.nameru if recipient_position else None,
            'status': status
        }

        return recipient

    async def _collect_approvers_by_document(self, document: DocumentModel, tutors_dict: dict, subdivision_dict: dict):
        approvers = await ApproverDAO(self.session_postgres).get_all_filtered(
            filters={
                ApproverModel.document_id: document.id,
                ApproverModel.is_recipient: False,
            }
        )

        approvers_response = []

        for approver in approvers:
            approver_user = tutors_dict.get(approver.approver_user.platonus_id)
            if approver_user is None:
                continue
            approver_position = subdivision_dict.get(approver.approver_user.platonus_id)

            approver_response = ApproverPerson(
                id=approver.approver_user.id,
                firstname=approver_user.firstname,
                lastname=approver_user.lastname,
                patronymic=approver_user.patronymic,
                role=approver_position.nameru if approver_position else None,
                avatar=None,
                status=approver.status
            )

            approvers_response.append(approver_response)

        return approvers_response

    async def _collect_user_documents(self, current_user: UserModel, category: str):
        if category == 'incoming':
            documents = await DocumentDAO(self.session_postgres).incoming(current_user.id)
        elif category == 'outgoing':
            documents = await DocumentDAO(self.session_postgres).outgoing(current_user.id)
        elif category == 'pending_execution':
            documents = await DocumentDAO(self.session_postgres).pending_execution(current_user.id)
        else:
            documents = await DocumentDAO(self.session_postgres).executed(current_user.id)

        result_incoming = []
        tutors_dict, subdivision_dict = await self._collect_tutor_and_subdivision_by_documents(documents)

        for document in documents:
            sender = await self._collect_sender_by_document(document)
            recipient = await self._collect_recipient(document, tutors_dict, subdivision_dict)
            approvers_response = await self._collect_approvers_by_document(document, tutors_dict, subdivision_dict)
            is_hidden = await HiddenDocumentDAO(self.session_postgres).is_hidden(current_user.id, document.id)

            sender_response = Person(
                id=document.author_id,
                firstname=sender['platonus_user'].firstname,
                lastname=sender['platonus_user'].lastname,
                patronymic=sender['platonus_user'].patronymic,
                role=sender['position'],
                avatar=None,
                status=sender['status']
            )

            recipient_response = Person(
                id=document.recipient_id,
                firstname=recipient['platonus_user'].firstname,
                lastname=recipient['platonus_user'].lastname,
                patronymic=recipient['platonus_user'].patronymic,
                role=recipient['position'],
                avatar=None,
                status=recipient['status']
            )

            result_incoming.append(
                OutgoingResponse(
                    id=document.id,
                    name=document.name,
                    sender=sender_response,
                    recipient=recipient_response,
                    approvers=approvers_response,
                    type=document.document_type.name_ru,
                    type_id=document.document_type_id,
                    create_datetime=document.created_at,
                    status=document.status,
                    is_hidden=is_hidden,
                )
            )

        return result_incoming

    @staticmethod
    async def _get_document_bytes_by_document(document: DocumentModel) -> bytes:
        document_path = (get_settings().STORAGE_DIRECTORY
                         / "docs"
                         / str(document.created_at.year)
                         / str(document.document_type_id)
                         / str(document.author_user.platonus_id)
                         / str(document.id)
                         / 'document.pdf'
                         )

        async with aiofiles.open(document_path, "rb") as f:
            return await f.read()

    @staticmethod
    async def _save_signature_to_file(
            document: DocumentModel,
            user_platonus_id: int,
            signature: str,
            is_sigex: bool
    ):
        document_directory = (get_settings().STORAGE_DIRECTORY
                              / "docs"
                              / str(document.created_at.year)
                              / str(document.document_type_id)
                              / str(document.author_user.platonus_id)
                              / str(document.id)
                              )
        prefix = "Base64-"

        if is_sigex:
            prefix = "Sigex-Base64-"

        async with aiofiles.open(document_directory / f"{prefix}{user_platonus_id}.cms", "w") as f:
            await f.write(signature)

    async def incoming(self, user: UserModel):
        return await self._collect_user_documents(user, 'incoming')

    async def outgoing(self, user: UserModel):
        return await self._collect_user_documents(user, 'outgoing')

    async def pending_execution(self, user: UserModel):
        return await self._collect_user_documents(user, 'pending_execution')

    async def executed(self, user: UserModel):
        return await self._collect_user_documents(user, 'executed')

    async def upload(self, data: DocumentUploadRequest, file: UploadFile, current_user: UserModel):
        file_content = await file.read()
        base64_string = base64.b64encode(file_content).decode('utf-8')
        user_ecp_info = NCANode().cms_verify(data.signature, base64_string)

        if not user_ecp_info:
            raise HTTPException(status_code=400, detail={"code": "INVALID_SIGNATURE", "message": "Invalid signature"})

        tutor: TutorModel = await TutorDAO(self.session_nitro).get_one_or_none(
            filters={
                TutorModel.TutorID: current_user.platonus_id
            }
        )

        if user_ecp_info.iin_number != tutor.iinplt:
            raise HTTPException(
                status_code=400,
                detail={"code": "IIN_MISMATCH","message": "The IIN used to sign the document does not match the IIN you are logged in with."}
            )

        sigex = Sigex()
        sigex_data = await sigex.register_document(
            document_name=data.document_name,
            user_signature=data.signature,
            file_bytes=file_content
        )

        recipient_user = await MigrateUserMysqlToPostgres(
            self.session_nitro,
            self.session_postgres
        ).migrate_by_tutor_id(
            tutor_id=data.recipient_id
        )

        if recipient_user is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "RECIPIENT_NOT_FOUND",
                    "message": "Recipient user not found"
                },
            )

        document = await DocumentDAO(self.session_postgres).add(
            author_id=current_user.id,
            recipient_id=recipient_user.id,
            document_type_id=data.document_type_id,
            name=data.document_name,
            sigex_id=sigex_data['sigex_document_id']
        )

        await ApproverDAO(self.session_postgres).add_if_not_exists(
            document_id=document.id,
            approver_id=recipient_user.id,
            is_recipient=True
        )

        if current_user.platonus_id:
            if current_user.is_student:
                current_user_data = await StudentDAO(self.session_nitro).get_one_or_none(
                    fields=[StudentModel.firstname, StudentModel.lastname, StudentModel.patronymic],
                    filters={
                        StudentModel.StudentID: current_user.platonus_id
                    }
                )
            else:
                current_user_data = await TutorDAO(self.session_nitro).get_one_or_none(
                    fields=[TutorModel.firstname, TutorModel.lastname, TutorModel.patronymic],
                    filters={
                        TutorModel.TutorID: current_user.platonus_id
                    }
                )
        else:
            current_user_data = await UserInfoDAO(self.session_postgres).get_one_or_none(
                filters={
                    UserInfoModel.user_id: current_user.id,
                }
            )

        first_initial = f"{current_user_data.firstname[0].upper()}."
        patronymic_initial = f" {current_user_data.patronymic[0].upper()}." if current_user_data.patronymic else ""
        shortname = f"{current_user_data.lastname} {first_initial}{patronymic_initial}".strip()

        await NotificationService(
            session_postgres=self.session_postgres
        ).send_notification(
            recipient_user_id=recipient_user.id,
            sender_user_id=current_user.id,
            sender_name=shortname,
            title='Новый документ на подпись',
            message=f'{data.document_name}',
            other_data={
                'type': 'incoming_document',
                'document_id': document.id,
            }
        )

        await self.session_postgres.refresh(document, attribute_names=["author_user"])
        author_platonus_id = document.author_user.platonus_id

        platonus_id = current_user.platonus_id if current_user.platonus_id else "no_platonus_id"

        document_directory = (get_settings().STORAGE_DIRECTORY
                              / "docs"
                              / datetime.now().strftime("%Y")
                              / str(document.document_type_id)
                              / str(author_platonus_id)
                              / str(document.id)
                              )

        document_directory.mkdir(parents=True, exist_ok=True)

        await self._save_signature_to_file(document, platonus_id, data.signature, False)
        await self._save_signature_to_file(document, platonus_id, sigex_data['sigex_cms'], True)

        async with aiofiles.open(document_directory / 'document.pdf', "wb") as out_file:
            await out_file.write(file_content)

        for approver_id in data.approver_user_ids:
            approver_user = await MigrateUserMysqlToPostgres(
                self.session_nitro,
                self.session_postgres
            ).migrate_by_tutor_id(
                tutor_id=approver_id
            )

            await ApproverDAO(self.session_postgres).add_if_not_exists(
                document_id=document.id,
                approver_id=int(approver_user.id),
                is_recipient=False
            )

    async def upload_custom(self):
        pass

    async def types_and_categories(self, user: UserModel, language: str) -> List[DocumentTypesAndCategory]:
        groups = await DocumentDAO(self.session_postgres).get_all_types_and_categories(user.id)
        response: List[DocumentTypesAndCategory] = []

        for group in groups:
            category_name = group.name_kz if language == "kz" else group.name_ru

            active_document_types = [
                DocumentType(
                    id=doc_type.id,
                    name=doc_type.name_kz if language == "kz" else doc_type.name_ru
                )
                for doc_type in group.document_types
                if doc_type.is_active
            ]

            category = DocumentCategory(
                id=group.id,
                name=category_name
            )

            response.append(
                DocumentTypesAndCategory(
                    category=category,
                    document_types=active_document_types
                )
            )

        return response

    async def sign(
            self,
            document_id: int,
            user_signature: str,
            user: UserModel,
            resolution: str | None,
            executors: list[int]
    ):
        document = await DocumentDAO(self.session_postgres).get_by_id(document_id)

        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        document_bytes = await self._get_document_bytes_by_document(document)
        base64_string = base64.b64encode(document_bytes).decode('utf-8')
        user_ecp_info = NCANode().cms_verify(user_signature, base64_string)

        if not user_ecp_info:
            raise HTTPException(status_code=400, detail="Invalid signature")

        tutor: TutorModel = await TutorDAO(self.session_nitro).get_one_or_none(
            filters={
                TutorModel.TutorID: user.platonus_id
            }
        )

        if user_ecp_info.iin_number != tutor.iinplt:
            raise HTTPException(
                status_code=400,
                detail="The IIN used to sign the document does not match the IIN you are logged in with."
            )

        sigex = Sigex()
        sigex_signature = await sigex.add_signature(document.sigex_id, user_signature)

        await ApproverDAO(self.session_postgres).set_status(
            document_id=document_id,
            approver_id=user.id,
            status=ApproverStatus.SIGNED
        )

        if resolution:
            await ApproverDAO(self.session_postgres).set_resolution(
                document_id=document_id,
                approver_id=user.id,
                resolution=resolution
            )

        if executors:
            for executor_id in executors:
                executor_user = await MigrateUserMysqlToPostgres(
                    self.session_nitro,
                    self.session_postgres
                ).migrate_by_tutor_id(
                    tutor_id=executor_id
                )

                await ExecutorDAO(self.session_postgres).add(
                    document_id=document_id,
                    executor_id=executor_user.id,
                )

        approvers = await ApproverDAO(self.session_postgres).get_all_filtered(
            filters={
                ApproverModel.document_id: document_id,
            }
        )

        is_all_signed = True

        for approver in approvers:
            if approver.status != ApproverStatus.SIGNED:
                is_all_signed = False
                break

        if is_all_signed:
            executors = await ExecutorDAO(self.session_postgres).get_all_filtered(
                filters={
                    ExecutorModel.document_id: document_id,
                }
            )

            if executors:
                await DocumentDAO(self.session_postgres).update(
                    filters={DocumentModel.id: document_id},
                    values={DocumentModel.status: DocumentStatus.ON_EXECUTION}
                )
            else:
                await DocumentDAO(self.session_postgres).update(
                    filters={DocumentModel.id: document_id},
                    values={DocumentModel.status: DocumentStatus.SIGNED}
                )

        await self._save_signature_to_file(document, user.platonus_id, user_signature, False)
        await self._save_signature_to_file(document, user.platonus_id, sigex_signature, True)

    async def cancel(self, document_id: int, approver_id: int):
        approver = await ApproverDAO(self.session_postgres).set_status(
            document_id=document_id,
            approver_id=approver_id,
            status=ApproverStatus.REJECTED
        )

        if approver is None:
            raise HTTPException(status_code=404, detail="Approver not found")

        await DocumentDAO(self.session_postgres).update(
            filters={DocumentModel.id: document_id},
            values={DocumentModel.status: DocumentStatus.REJECTED}
        )

    async def execute(self, document_id: int, executor_id: int):
        document = await DocumentDAO(self.session_postgres).get_by_id(document_id)

        if document.status != DocumentStatus.ON_EXECUTION:
            raise HTTPException(status_code=400, detail="Document is not on execution")

        executor = await ExecutorDAO(self.session_postgres).set_status(
            document_id=document_id,
            executor_id=executor_id,
            status=ExecutorStatus.COMPLETED
        )

        if executor is None:
            raise HTTPException(status_code=404, detail="Executor not found")

        executors = await ExecutorDAO(self.session_postgres).get_all_filtered(
            filters={
                ExecutorModel.document_id: document_id,
            }
        )

        is_all_completed = True

        for executor in executors:
            if executor.status != ExecutorStatus.COMPLETED:
                is_all_completed = False
                break

        if is_all_completed:
            await DocumentDAO(self.session_postgres).update(
                filters={DocumentModel.id: document_id},
                values={DocumentModel.status: DocumentStatus.EXECUTED}
            )

    async def revoke(self, user_id:int, document_id: int):
        document = await DocumentDAO(self.session_postgres).get_by_id(document_id)

        if document.author_id != user_id:
            raise HTTPException(status_code=403, detail="You are not the author of this document")

        await DocumentDAO(self.session_postgres).update(
            filters={DocumentModel.id: document_id},
            values={DocumentModel.status: DocumentStatus.REVOKED}
        )

    async def hide(self, user_id: int, document_id: int):
        await HiddenDocumentDAO(self.session_postgres).hide(
            user_id=user_id,
            document_id=document_id
        )

    async def unhide(self, user_id: int, document_id: int):
        await HiddenDocumentDAO(self.session_postgres).unhide(
            user_id=user_id,
            document_id=document_id
        )

    async def pdf(self, document_id: int):
        document = await DocumentDAO(self.session_postgres).get_by_id(document_id)

        document_path = (get_settings().STORAGE_DIRECTORY
                              / "docs"
                              / datetime.now().strftime("%Y")
                              / str(document.document_type_id)
                              / str(document.author_user.platonus_id)
                              / str(document.id)
                              / 'document.pdf'
                              )

        if not document_path.exists():
            raise HTTPException(status_code=404, detail="Document not found")

        return document_path

    async def samples(self):
        sample_documents = await SampleDocumentDAO(self.session_postgres).get_all_filtered(
            filters={SampleDocumentModel.is_active: True}
        )

        result = [
            SampleDocument(
                id=doc.id,
                name=doc.name_ru,  # или name_kz — зависит от языка, который ты хочешь
                group=doc.sample_document_group.name_ru,  # если в группе есть поле name_ru
                group_id=doc.sample_document_group_id
            )
            for doc in sample_documents
        ]

        return result

    @staticmethod
    async def sample_pdf(sample_document_id: int):
        base_dir = get_settings().STORAGE_DIRECTORY / "sample_documents"

        # пути к DOCX и PDF
        document_path = base_dir / f"{sample_document_id}.docx"
        pdf_path = base_dir / f"{sample_document_id}.pdf"

        # если PDF уже есть — сразу возвращаем
        if pdf_path.exists():
            return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)

        # если DOCX отсутствует — ошибка
        if not document_path.exists():
            raise HTTPException(status_code=404, detail="DOCX файл не найден")

        # конвертация docx → pdf через libreoffice (в ту же директорию)
        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(base_dir),
            str(document_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка конвертации DOCX в PDF: {stderr.decode()}"
            )

        # после конвертации проверяем, что PDF появился
        if not pdf_path.exists():
            raise HTTPException(status_code=500, detail="Не удалось создать PDF-файл")

        return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)

    @staticmethod
    async def sample_download(sample_document_id: int):
        base_dir = get_settings().STORAGE_DIRECTORY / "sample_documents"
        document_path = base_dir / f"{sample_document_id}.docx"

        if not document_path.exists():
            raise HTTPException(status_code=404, detail="DOCX файл не найден")

        return FileResponse(
            path=document_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=document_path.name
        )

