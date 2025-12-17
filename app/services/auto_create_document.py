from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.core.settings import get_settings

from app.models.postgres import (
    User as UserModel,
)

from app.models.mysql.nitro import (
    Tutor as TutorModel,
    StructuralSubdivision as StructuralSubdivisionModel,
    TutorPositions as TutorPositionsModel
)

from app.dao.mysql import TutorDAO


class AutoCreateDocument:
    def __init__(
            self,
            session_nitro: AsyncSession,
            session_postgres: AsyncSession,
            document_type_id: int,
            current_user: UserModel,
            language: str = 'ru'
    ):
        self.session_nitro = session_nitro
        self.session_postgres = session_postgres
        self.document_type_id = document_type_id
        self.current_user = current_user
        self.language = language

    async def make_107(
            self,
            data: dict,
    ) -> bytes:
        template_dir_path = (
                get_settings().STORAGE_DIRECTORY /
                "auto_create_document_templates" /
                str(self.document_type_id)
        )

        rector_data = await TutorDAO(
            self.session_nitro
        ).get_one_or_none(
            fields=[
                TutorModel.firstname,
                TutorModel.lastname,
                TutorModel.patronymic
            ],
            filters={
                TutorModel.job_title_int: 383
            }
        )

        user_data = await TutorDAO(
            self.session_nitro
        ).join_structural_subdivision_and_tutor_positions(
            fields=[
                TutorModel.firstname,
                TutorModel.lastname,
                TutorModel.patronymic,
                StructuralSubdivisionModel.namekz,
                TutorPositionsModel.NameKZ
            ],
            filters={
                TutorModel.TutorID: self.current_user.platonus_id
            }
        )

        rector_shortname = f"{rector_data.lastname} {rector_data.firstname[0]}. {rector_data.patronymic[0]}."
        sender_shortname = ''
        structural_subdivision = ''
        post = ''

        for _tutor, subdivision, position in user_data:
            sender_shortname = f"{_tutor.lastname} {_tutor.firstname[0]}."

            if len(_tutor.patronymic) > 0:
                sender_shortname += f" {_tutor.patronymic[0]}."

            structural_subdivision = subdivision.nameru if self.language == "ru" else subdivision.namekz
            post = position.NameRU if self.language == "ru" else position.NameKZ

        approver_user_ids = data.get("approver_user_ids")

        approvers = await TutorDAO(
            self.session_nitro
        ).join_structural_subdivision_and_tutor_positions(
            fields=[
                TutorModel.firstname,
                TutorModel.lastname,
                TutorModel.patronymic,
                StructuralSubdivisionModel.nameru,
                StructuralSubdivisionModel.namekz,
                TutorPositionsModel.NameRU,
                TutorPositionsModel.NameKZ
            ],
            filters={
                TutorModel.TutorID: approver_user_ids
            }
        )

        approvers_data = []

        for row in approvers:
            tutor, subdivision, position_info = row

            f_initial = f"{tutor.firstname[0]}." if tutor.firstname else ""
            p_initial = f"{tutor.patronymic[0]}." if tutor.patronymic else ""

            short_fio = f"{tutor.lastname} {f_initial}{p_initial}"
            job_title = position_info.NameRU if self.language == 'ru' else position_info.NameKZ

            approvers_data.append({
                "position": job_title,
                "fio": short_fio
            })

        vice_id = data.get("vice_id")
        vice = ''

        if vice_id:
            vice_data = await TutorDAO(
                self.session_nitro
            ).join_structural_subdivision_and_tutor_positions(
                fields=[
                    TutorModel.firstname,
                    TutorModel.lastname,
                    TutorModel.patronymic,
                    StructuralSubdivisionModel.nameru,
                    StructuralSubdivisionModel.namekz,
                    TutorPositionsModel.NameRU,
                    TutorPositionsModel.NameKZ
                ],
                filters={
                    TutorModel.TutorID: vice_id
                }
            )

            for row in vice_data:
                tutor, subdivision, position_info = row

                f_initial = f"{tutor.firstname[0]}." if tutor.firstname else ""
                p_initial = f"{tutor.patronymic[0]}." if tutor.patronymic else ""

                vice = f"{tutor.lastname} {f_initial}{p_initial}, {position_info.NameRU if self.language == 'ru' else position_info.NameKZ}"

        env = Environment(loader=FileSystemLoader(template_dir_path))
        template = env.get_template(f"template_{self.language}.html")

        html = template.render(
            rector_shortname=rector_shortname,
            structural_subdivision=structural_subdivision,
            post=post,
            sender_shortname=sender_shortname,
            trip_purpose=data.get("trip_purpose"),
            trip_date_start=data.get("trip_date_start"),
            trip_date_end=data.get("trip_date_end"),
            destinations=data.get("destinations"),
            funding_source=data.get("funding_source"),
            vice=vice,
            approvers=approvers_data
        )

        HTML(string=html).write_pdf("document.pdf")

        return HTML(string=html).write_pdf()
