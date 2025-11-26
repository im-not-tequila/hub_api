from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc, desc, update as sa_update
from sqlalchemy.orm import load_only
from typing import Generic, TypeVar, Type, Sequence


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

    async def get_all_filtered(
        self,
        filters: dict = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,  # пример: "id:desc" или "created_at:asc"
    ):
        stmt = select(self.model)

        # Фильтрация
        if filters:
            for field, values in filters.items():
                # column = getattr(self.model, field, None)
                # if column is None:
                #     continue  # игнорируем несуществующие поля

                if isinstance(values, list):
                    stmt = stmt.where(field.in_(values))
                else:
                    stmt = stmt.where(field == values)

        # Сортировка
        if order_by:
            try:
                field, direction = order_by.split(":")
                column = getattr(self.model, field)
                if direction.lower() == "desc":
                    stmt = stmt.order_by(desc(column))
                else:
                    stmt = stmt.order_by(asc(column))
            except Exception:
                # fallback: сортировка по id desc
                stmt = stmt.order_by(desc(self.model.id))
        else:
            # сортировка по умолчанию
            stmt = stmt.order_by(desc(self.model.id))

        # Пагинация
        stmt = stmt.limit(limit).offset(offset)

        # Выполнение запроса
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_one_or_none(
            self,
            filters: dict = None,
            fields: Sequence | None = None, **filter_by
    ) -> ModelType | None:
        """
        Асинхронно находит и возвращает один экземпляр модели по указанным критериям или None.

        Аргументы:
            **filter_by: Критерии фильтрации в виде именованных параметров.

        Возвращает:
            Экземпляр модели или None, если ничего не найдено.
        """

        stmt = select(self.model).limit(1)

        if fields:
            stmt = stmt.options(load_only(*fields))

        if filters:
            for field, values in filters.items():
                if isinstance(values, list):
                    stmt = stmt.where(field.in_(values))
                else:
                    stmt = stmt.where(field == values)

        result = await self.session.execute(stmt)

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

    async def update(self, filters: dict, values: dict):
        """
        Асинхронно обновляет один или несколько экземпляров модели по фильтрам.

        Аргументы:
            filters: dict с SQLAlchemy условиями (например: {Model.id: 1, Model.user_id: 2})
            values: dict с новыми значениями (например: {Model.is_read: True})

        Возвращает:
            Список обновлённых экземпляров модели.
        """

        # --- SELECT: найти подходящие записи ---
        stmt_select = select(self.model)

        if filters:
            for field, val in filters.items():
                column = getattr(self.model, field.key if hasattr(field, "key") else field)
                if isinstance(val, list):
                    stmt_select = stmt_select.where(column.in_(val))
                else:
                    stmt_select = stmt_select.where(column == val)

        result = await self.session.execute(stmt_select)
        instances = result.scalars().all()

        if not instances:
            return []

        # --- UPDATE: обновляем найденные записи ---
        ids = [obj.id for obj in instances]
        stmt_update = (
            sa_update(self.model)
            .where(self.model.id.in_(ids))
            .values({field.key: val for field, val in values.items()})
            .returning(self.model)
        )

        result = await self.session.execute(stmt_update)
        await self.session.commit()

        return result.scalars().all()

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

