from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.mysql import StructuralSubdivisionDAO

LANG_TO_NAME_FIELD = {
    'ru': 'nameru',
    'kz': 'namekz',
    'en': 'nameen',
}


class StructuralSubdivisionService:
    def __init__(self, session_nitro: AsyncSession):
        self.session_nitro = session_nitro

    async def get_subordinates(self, subdivision_id: int, lang: str) -> list[dict]:
        name_field = LANG_TO_NAME_FIELD.get(lang, 'nameru')
        dao = StructuralSubdivisionDAO(self.session_nitro)
        return await dao.get_subordinates(subdivision_id, name_field)
