from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.mysql import CafedraDAO
from app.models.mysql.nitro import Cafedra as CafedraModel

LANG_TO_NAME_FIELD = {
    'ru': 'cafedraNameRU',
    'kz': 'cafedraNameKZ',
    'en': 'cafedraNameEN',
}


class StructureService:
    def __init__(self, session_nitro: AsyncSession):
        self.session_nitro = session_nitro

    async def get_all_used_cafedras(self, lang: str) -> list[dict]:
        dao = CafedraDAO(self.session_nitro)
        rows = await dao.get_all_filtered(
            filters={CafedraModel.used: 1},
            limit=10_000,
            order_by='cafedraID:asc',
        )

        name_attr = LANG_TO_NAME_FIELD.get(lang, 'cafedraNameRU')
        return [
            {
                'id': row.cafedraID,
                'name': getattr(row, name_attr),
                'faculty_id': row.FacultyID,
            }
            for row in rows
        ]
