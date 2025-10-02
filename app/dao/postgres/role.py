from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import cast

from app.models.postgres import Role


class RoleDao:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_roles_by_ids(self, role_ids: list[int]) -> list[Role]:
        stmt = select(Role).where(Role.id.in_(role_ids))

        result = await self.session.execute(stmt)
        rows = cast(list[Role], result.scalars().all())

        return rows
