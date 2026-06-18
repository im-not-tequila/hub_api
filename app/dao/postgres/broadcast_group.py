from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import PostgresDao
from app.models.postgres.broadcast_group import BroadcastGroup
from app.models.postgres.broadcast_group_member import BroadcastGroupMember
from app.models.postgres.broadcast_group_role import BroadcastGroupRole
from app.models.postgres.user_role import UserRole


class BroadcastGroupDAO(PostgresDao):
    def __init__(self, session: AsyncSession):
        super().__init__(session, BroadcastGroup)

    async def get_groups_for_user(self, user_id: int, is_admin: bool) -> list[BroadcastGroup]:
        """
        Возвращает группы, к которым пользователь имеет доступ.
        Администратор видит все группы.
        Обычный пользователь видит только группы, у которых есть совпадение
        между его ролями и разрешёнными ролями группы.
        """
        if is_admin:
            result = await self.session.execute(select(BroadcastGroup))
            return list(result.scalars().all())

        user_role_ids_subq = (
            select(UserRole.role_id).where(UserRole.user_id == user_id)
        )
        accessible_group_ids_subq = (
            select(BroadcastGroupRole.group_id)
            .where(BroadcastGroupRole.role_id.in_(user_role_ids_subq))
        )
        stmt = select(BroadcastGroup).where(
            BroadcastGroup.id.in_(accessible_group_ids_subq)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def user_can_send(self, user_id: int, group_id: int) -> bool:
        """Проверяет, есть ли у пользователя роль, дающая доступ к рассылке в данную группу."""
        user_role_ids_subq = (
            select(UserRole.role_id).where(UserRole.user_id == user_id)
        )
        stmt = (
            select(BroadcastGroupRole.id)
            .where(
                BroadcastGroupRole.group_id == group_id,
                BroadcastGroupRole.role_id.in_(user_role_ids_subq),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_member(self, group_id: int, user_id: int) -> BroadcastGroupMember | None:
        stmt = select(BroadcastGroupMember).where(
            BroadcastGroupMember.group_id == group_id,
            BroadcastGroupMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_member(
        self, group_id: int, user_id: int, added_by_user_id: int
    ) -> BroadcastGroupMember:
        existing = await self.get_member(group_id, user_id)
        if existing:
            return existing
        member = BroadcastGroupMember(
            group_id=group_id,
            user_id=user_id,
            added_by_user_id=added_by_user_id,
        )
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def remove_member(self, group_id: int, user_id: int) -> bool:
        stmt = delete(BroadcastGroupMember).where(
            BroadcastGroupMember.group_id == group_id,
            BroadcastGroupMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def get_group_role(self, group_id: int, role_id: int) -> BroadcastGroupRole | None:
        stmt = select(BroadcastGroupRole).where(
            BroadcastGroupRole.group_id == group_id,
            BroadcastGroupRole.role_id == role_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_role(self, group_id: int, role_id: int) -> BroadcastGroupRole:
        existing = await self.get_group_role(group_id, role_id)
        if existing:
            return existing
        group_role = BroadcastGroupRole(group_id=group_id, role_id=role_id)
        self.session.add(group_role)
        await self.session.flush()
        await self.session.refresh(group_role)
        return group_role

    async def remove_role(self, group_id: int, role_id: int) -> bool:
        stmt = delete(BroadcastGroupRole).where(
            BroadcastGroupRole.group_id == group_id,
            BroadcastGroupRole.role_id == role_id,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def get_member_user_ids(self, group_id: int) -> list[int]:
        stmt = select(BroadcastGroupMember.user_id).where(
            BroadcastGroupMember.group_id == group_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
