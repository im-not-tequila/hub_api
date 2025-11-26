from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import Depends

from app.dao.base import PostgresDao
from app.dao.postgres.role import RoleDao
from app.models.postgres import User, UserRole
from sqlalchemy.ext.asyncio import AsyncSession


class UserDAO(PostgresDao):
    def __init__(
            self,
            session: AsyncSession
    ):
        super().__init__(session, User)

    async def add_roles(self, user_id: int, role_ids: list[int]):
        """
        Добавляет роли пользователю, если их еще нет.

        Args:
            user_id (int): ID пользователя.
            role_ids (list[int]): Список ID ролей, которые нужно добавить.

        Returns:
            User: Обновленный пользователь с ролями.
        """
        # Получаем пользователя с текущими ролями
        stmt = (
            select(self.model)
            .options(selectinload(self.model.user_roles).selectinload(UserRole.role))
            .where(self.model.id == user_id)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        roles_to_add = await RoleDao(self.session).get_roles_by_ids(role_ids)
        existing_role_ids = {ur.role_id for ur in user.user_roles}

        for role in roles_to_add:
            if role.id not in existing_role_ids:
                user.user_roles.append(UserRole(role=role))

        await self.session.commit()
        await self.session.refresh(user)

        return user
