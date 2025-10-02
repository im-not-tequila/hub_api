import aiofiles
import base64

from datetime import datetime
from typing import List

from fastapi import HTTPException, UploadFile

from app.dao.mysql import TutorDAO, StudentDAO
from app.services.ncanode import NCANode
from app.core.settings import get_settings
from app.db.session import get_postgres_session, get_mysql_session
from app.dao.postgres import DocumentDAO, ApproverDAO, ExecutorDAO
from app.services.sigex import Sigex
from app.schemas import DocumentUploadRequest, DocumentTypesAndCategory, DocumentCategory, DocumentType, OutgoingResponse, Person, ApproverPerson, DocumentStatus
from app.models.postgres import (
    User as UserModel,
    Approver as ApproverModel,
    Document as DocumentModel,
    Executor as ExecutorModel,
    ApproverStatus,
    ExecutorStatus
)
from app.models.mysql import Tutor as TutorModel
from app.dao.migrate_user import MigrateUserMysqlToPostgres


class DocumentService:
    async def upload(self, data: DocumentUploadRequest, file: UploadFile, current_user: UserModel):
        file_content = await file.read()
        base64_string = base64.b64encode(file_content).decode('utf-8')
        user_ecp_info = NCANode().cms_verify(data.cms, base64_string)

        if not user_ecp_info:
            raise HTTPException(status_code=400, detail="Invalid signature")

        sigex = Sigex()
        sigex_data = await sigex.register_document(
            document_name=data.document_name,
            user_signature=data.cms,
            file_bytes=file_content
        )

        async with get_mysql_session() as mysql_session:
            async with get_postgres_session() as postgres_session:
                recipient_user = await MigrateUserMysqlToPostgres(
                    mysql_session,
                    postgres_session
                ).migrate_by_tutor_id(
                    tutor_id=data.recipient_id
                )

                if recipient_user is None:
                    raise HTTPException(status_code=400, detail="Recipient user not found")

                document = await DocumentDAO(postgres_session).add(
                    author_id=current_user.id,
                    recipient_id=recipient_user.id,
                    document_type_id=data.document_type_id,
                    name=data.document_name,
                    sigex_id=sigex_data['sigex_document_id']
                )

                await ApproverDAO(postgres_session).add(
                    document_id=document.id,
                    approver_id=recipient_user.id,
                    is_recipient=True
                )

        platonus_id = current_user.platonus_id if current_user.platonus_id else "no_platonus_id"

        document_directory = (get_settings().STORAGE_DIRECTORY
                              / "docs"
                              / datetime.now().strftime("%Y")
                              / str(document.document_type_id)
                              / str(document.author_user.platonus_id)
                              / str(document.id)
                              )

        document_directory.mkdir(parents=True, exist_ok=True)

        await self._save_signature_to_file(document, platonus_id, data.cms, False)
        await self._save_signature_to_file(document, platonus_id, sigex_data['sigex_cms'], True)

        async with aiofiles.open(document_directory / 'document.pdf', "wb") as out_file:
            await out_file.write(file_content)

        async with get_mysql_session() as mysql_session:
            async with get_postgres_session() as postgres_session:
                for approver_id in data.approver_user_ids:
                    recipient_user = await MigrateUserMysqlToPostgres(
                        mysql_session,
                        postgres_session
                    ).migrate_by_tutor_id(
                        tutor_id=approver_id
                    )

                    await ApproverDAO(postgres_session).add(
                        document_id=document.id,
                        approver_id=recipient_user.id,
                        is_recipient=False
                    )

                # approvers_data = [
                #     {"document_id": document.id, "approver_user_id": user_id}
                #     for user_id in data.approver_user_ids
                # ]
                #
                # await ApproverDAO(postgres_session).bulk_add(approvers_data)

    @staticmethod
    async def types_and_categories(user: UserModel, language: str) -> List[DocumentTypesAndCategory]:
        async with get_postgres_session() as postgres_session:
            groups = await DocumentDAO(postgres_session).get_all_types_and_categories(user.id)
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

    @staticmethod
    async def _collect_tutor_and_subdivision_by_documents(documents: list[DocumentModel]):
        async with get_mysql_session() as mysql_session:
            async with get_postgres_session() as postgres_session:
                document_ids = []
                platonus_ids = []

                for document in documents:
                    platonus_ids.append(document.recipient_user.platonus_id)
                    document_ids.append(document.id)

                all_approvers = await ApproverDAO(postgres_session).get_all_filtered(
                    filters={
                        ApproverModel.document_id: document_ids,
                    }
                )

                for approver in all_approvers:
                    platonus_ids.append(approver.approver_user.platonus_id)

                tutors = await TutorDAO(mysql_session).get_tutors_and_position(
                    filters={
                        TutorModel.TutorID: platonus_ids,
                    }
                )

                tutors_dict = {}
                subdivision_dict = {}

                for tutor, subdivision in tutors:
                    tutors_dict[tutor.TutorID] = tutor
                    subdivision_dict[tutor.TutorID] = subdivision

                return tutors_dict, subdivision_dict

    @staticmethod
    async def _collect_sender_by_document(document: DocumentModel):
        async with get_mysql_session() as mysql_session:
            if document.author_user.is_student:
                sender = await StudentDAO(mysql_session).get_by_id(document.author_user.platonus_id)
                sender_position = 'Студент'
            else:
                sender = await TutorDAO(mysql_session).get_one_or_none(TutorID=document.author_user.platonus_id)
                sender_position = 'Сотрудник университета'
                all_tutors_and_position = await TutorDAO(mysql_session).get_tutors_and_position(
                    filters={
                        TutorModel.TutorID: document.author_user.platonus_id,
                    }
                )

                for _, position in all_tutors_and_position:
                    if position:
                        sender_position = position.nameru

                    break

            return {
                'platonus_user': sender,
                'hub_user': document.author_user,
                'position': sender_position,
                'status': DocumentStatus.SIGNED
            }

    @staticmethod
    async def _collect_recipient(document: DocumentModel, current_user: UserModel, tutors_dict: dict, subdivision_dict: dict):
        async with get_postgres_session() as postgres_session:
            recipient_approver = await ApproverDAO(postgres_session).get_one_or_none(
                document_id=document.id,
                approver_id=document.recipient_id,
                is_recipient=True
            )

            if document.recipient_id == current_user.id:
                if recipient_approver.status == ApproverStatus.REJECTED:
                    status = DocumentStatus.REJECTED_BY_YOU
                elif recipient_approver.status == ApproverStatus.SIGNED:
                    status = DocumentStatus.SIGNED_BY_YOU
                else:
                    status = DocumentStatus.NOT_SIGNED_BY_YOU
            else:
                if recipient_approver.status == ApproverStatus.REJECTED:
                    status = DocumentStatus.REJECTED
                elif recipient_approver.status == ApproverStatus.SIGNED:
                    status = DocumentStatus.SIGNED
                else:
                    status = DocumentStatus.PENDING

        recipient = {
            'platonus_user': tutors_dict.get(document.recipient_user.platonus_id),
            'hub_user': document.recipient_user,
            'position': subdivision_dict.get(document.recipient_user.platonus_id).nameru,
            'status': status
        }

        return recipient

    @staticmethod
    async def _collect_approvers_by_document(document: DocumentModel, tutors_dict: dict, subdivision_dict: dict):
        async with get_postgres_session() as postgres_session:
            approvers = await ApproverDAO(postgres_session).get_all_filtered(
                filters={
                    ApproverModel.document_id: document.id,
                    ApproverModel.is_recipient: False,
                }
            )

            is_cancelled = False
            is_all_signed = True
            approvers_response = []

            for approver in approvers:
                approver_user = tutors_dict.get(approver.approver_user.platonus_id)
                approver_position = subdivision_dict.get(approver.approver_user.platonus_id)

                if approver.status != ApproverStatus.SIGNED:
                    is_all_signed = False

                if approver.status == ApproverStatus.REJECTED:
                    is_cancelled = True

                approver_response = ApproverPerson(
                    id=approver.approver_user.id,
                    firstname=approver_user.firstname,
                    lastname=approver_user.lastname,
                    patronymic=approver_user.patronymic,
                    role=approver_position.nameru,
                    avatar=None,
                    status=approver.status
                )

                approvers_response.append(approver_response)

            return approvers_response, is_cancelled, is_all_signed

    async def collect_user_documents(self, current_user: UserModel, category: str):
        async with get_postgres_session() as postgres_session:
            if category == 'incoming':
                documents = await DocumentDAO(postgres_session).incoming(current_user.id)
            elif category == 'outgoing':
                documents = await DocumentDAO(postgres_session).outgoing(current_user.id)
            elif category == 'pending_execution':
                documents = await DocumentDAO(postgres_session).pending_execution(current_user.id)
            else:
                documents = await DocumentDAO(postgres_session).executed(current_user.id)

            result_incoming = []
            tutors_dict, subdivision_dict = await self._collect_tutor_and_subdivision_by_documents(documents)

            for document in documents:
                sender = await self._collect_sender_by_document(document)
                recipient = await self._collect_recipient(document, current_user, tutors_dict, subdivision_dict)
                approvers_response, is_cancelled, is_all_signed = await self._collect_approvers_by_document(document, tutors_dict, subdivision_dict)

                if category == 'incoming':
                    document_status = recipient['status']
                elif category == 'outgoing':
                    if is_cancelled or recipient['status'] == DocumentStatus.REJECTED:
                        document_status = DocumentStatus.REJECTED
                    elif is_all_signed and recipient['status'] == DocumentStatus.SIGNED:
                        document_status = DocumentStatus.SIGNED
                    else:
                        document_status = DocumentStatus.PENDING
                else:
                    executor: ExecutorModel = await ExecutorDAO(postgres_session).get_one_or_none(
                        document_id=document.id,
                        executor_id=current_user.id
                    )

                    if executor:
                        if executor.status == ExecutorStatus.PENDING_EXECUTION:
                            document_status = DocumentStatus.NOT_EXECUTED_BY_YOU
                        else:
                            document_status = DocumentStatus.EXECUTED_BY_YOU


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
                        status=document_status
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

    async def sign(
            self,
            document_id: int,
            user_signature: str,
            user: UserModel,
            resolution: str | None,
            executors: list[int]
    ):
        async with get_postgres_session() as postgres_session:
            document = await DocumentDAO(postgres_session).get_by_id(document_id)

        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        document_bytes = await self._get_document_bytes_by_document(document)
        base64_string = base64.b64encode(document_bytes).decode('utf-8')
        user_ecp_info = NCANode().cms_verify(user_signature, base64_string)

        if not user_ecp_info:
            raise HTTPException(status_code=400, detail="Invalid signature")

        async with get_mysql_session() as mysql_session:
            tutor: TutorModel = await TutorDAO(mysql_session).get_one_or_none(TutorID=user.platonus_id)

            if user_ecp_info.iin_number != tutor.iinplt:
                raise HTTPException(
                    status_code=400,
                    detail="The IIN used to sign the document does not match the IIN you are logged in with."
                )

        sigex = Sigex()
        sigex_signature = await sigex.add_signature(document.sigex_id, user_signature)

        async with get_postgres_session() as postgres_session:
            await ApproverDAO(postgres_session).set_status(
                document_id=document_id,
                approver_id=user.id,
                status=ApproverStatus.SIGNED
            )

            if resolution:
                await ApproverDAO(postgres_session).set_resolution(
                    document_id=document_id,
                    approver_id=user.id,
                    resolution=resolution
                )

            if executors:
                async with get_mysql_session() as mysql_session:
                    for executor_id in executors:
                        executor_user = await MigrateUserMysqlToPostgres(
                            mysql_session,
                            postgres_session
                        ).migrate_by_tutor_id(
                            tutor_id=executor_id
                        )

                        await ExecutorDAO(postgres_session).add(
                            document_id=document_id,
                            executor_id=executor_user.id,
                        )

        await self._save_signature_to_file(document, user.platonus_id, user_signature, False)
        await self._save_signature_to_file(document, user.platonus_id, sigex_signature, True)

    @staticmethod
    async def execute(document_id: int, executor_id: int):
        async with get_postgres_session() as postgres_session:
            executor = await ExecutorDAO(postgres_session).set_status(
                document_id=document_id,
                executor_id=executor_id,
                status=ExecutorStatus.COMPLETED
            )

            if executor is None:
                raise HTTPException(status_code=404, detail="Executor not found")

    @staticmethod
    async def pdf(document_id: int):
        async with get_postgres_session() as postgres_session:
            document = await DocumentDAO(postgres_session).get_by_id(document_id)

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
