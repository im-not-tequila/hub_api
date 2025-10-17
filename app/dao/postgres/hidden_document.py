from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres import HiddenDocument


class HiddenDocumentDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def hide(self, user_id: int, document_id: int):
        hidden = HiddenDocument(user_id=user_id, document_id=document_id)
        self.session.add(hidden)
        await self.session.commit()

        return hidden

    async def unhide(self, user_id: int, document_id: int):
        await self.session.execute(
            delete(HiddenDocument)
            .where(HiddenDocument.user_id == user_id)
            .where(HiddenDocument.document_id == document_id)
        )

        await self.session.commit()

    async def is_hidden(self, user_id: int, document_id: int) -> bool:
        result = await self.session.execute(
            select(HiddenDocument)
            .where(HiddenDocument.user_id == user_id)
            .where(HiddenDocument.document_id == document_id)
        )

        return result.scalar_one_or_none() is not None
