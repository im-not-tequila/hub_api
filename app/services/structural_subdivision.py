from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.mysql import StructuralSubdivisionDAO
from app.models.mysql.nitro import StructuralSubdivision as StructuralSubdivisionModel

LANG_TO_NAME_FIELD = {
    'ru': 'nameru',
    'kz': 'namekz',
    'en': 'nameen',
}


class StructuralSubdivisionService:
    def __init__(self, session_nitro: AsyncSession):
        self.session_nitro = session_nitro

    async def get_all_active(self, lang: str) -> list[dict]:
        dao = StructuralSubdivisionDAO(self.session_nitro)
        rows = await dao.get_all_filtered(
            filters={
                StructuralSubdivisionModel.deleted: 0,
                StructuralSubdivisionModel.is_closed: 0,
            },
            limit=10_000,
            order_by='id:asc',
        )
        name_attr = LANG_TO_NAME_FIELD.get(lang, 'nameru')
        return [
            {
                'id': r.id,
                'dean': r.dean,
                'pre': r.pre,
                'name': getattr(r, name_attr),
                'subdivision_type': r.subdivision_type,
                'faculty_cafedra_id': r.faculty_cafedra_id,
            }
            for r in rows
        ]

    async def get_subordinates(self, subdivision_id: int, lang: str) -> list[dict]:
        name_field = LANG_TO_NAME_FIELD.get(lang, 'nameru')
        dao = StructuralSubdivisionDAO(self.session_nitro)
        return await dao.get_subordinates(subdivision_id, name_field)
