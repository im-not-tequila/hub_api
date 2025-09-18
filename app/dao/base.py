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

    async def bulk_add(self, objects_data: list[dict]):
        """
        Асинхронно добавляет несколько записей в таблицу за один коммит.

        Аргументы:
            objects_data: Список словарей, где каждый словарь — поля для одной записи.

        Возвращает:
            Список созданных экземпляров модели.
        """
        new_instances = [self.model(**data) for data in objects_data]

        self.session.add_all(new_instances)
        await self.session.commit()

        # Обновим экземпляры, чтобы получить ID и server_default
        for instance in new_instances:
            await self.session.refresh(instance)

        return new_instances
    
    async def update(self, obj_id: int, **values):
        """
        Асинхронно обновляет существующий экземпляр модели по его ID.

        Аргументы:
            obj_id: ID объекта, который нужно обновить.
            **values: Именованные параметры для обновления полей модели.

        Возвращает:
            Обновленный экземпляр модели или None, если объект не найден.
        """
        stmt = select(self.model).where(self.model.id == obj_id)
        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()

        if not instance:
            return None

        for key, value in values.items():
            setattr(instance, key, value)

        await self.session.commit()
        await self.session.refresh(instance)

        return instance
