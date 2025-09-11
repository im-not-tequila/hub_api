from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Generic, TypeVar, Type


ModelType = TypeVar("ModelType")


class BaseDAO(Generic[ModelType]):
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, obj_id: int):
        stmt = select(self.model).where(self.model.id == obj_id)
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0):
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)

        return result.scalars().all()

    async def get_one_or_none(self, **filter_by):
        """
        Асинхронно находит и возвращает один экземпляр модели по указанным критериям или None.

        Аргументы:
            **filter_by: Критерии фильтрации в виде именованных параметров.

        Возвращает:
            Экземпляр модели или None, если ничего не найдено.
        """

        query = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(query)

        return result.scalar_one_or_none()


class MySQLDao(BaseDAO):
    def __init__(self, session, model):
        super().__init__(session, model)


class PostgresDao(BaseDAO):
    def __init__(self, session, model):
        super().__init__(session, model)

    async def add(self, **values):
        """
        Асинхронно создает новый экземпляр модели с указанными значениями.

        Аргументы:
            **values: Именованные параметры для создания нового экземпляра модели.

        Возвращает:
            Созданный экземпляр модели.
        """

        new_instance = self.model(**values)
        self.session.add(new_instance)

        await self.session.commit()
        await self.session.refresh(new_instance)

        return new_instance
