import datetime

from typing import cast, Sequence
from collections import defaultdict

from app.dao.base import MySQLDao
from app.models.mysql.nitro import Tutor, TutorCafedra, Cafedra, TutorPositions, Faculty, StructuralSubdivision, Building
from app.models.mysql.perco import Personcontrol, Control
from sqlalchemy import select, func
from sqlalchemy.orm import load_only
from sqlalchemy.ext.asyncio import AsyncSession


class TutorDAO(MySQLDao):
    def __init__(
            self,
            session_nitro: AsyncSession,
            session_perco: AsyncSession = None
    ):
        super().__init__(session_nitro, Tutor)
        self.session_perco = session_perco

    async def get_tutor_positions_pps(self, tutor_id: int, lang: str = "RU"):
        name_column = getattr(TutorPositions, f"Name{lang}")

        stmt = (
            select(
                TutorCafedra.type,
                Cafedra.cafedraID,
                Cafedra.FacultyID,
                name_column.label("position_name")
            )
            .join(Tutor, TutorCafedra.tutorID == Tutor.TutorID)
            .join(Cafedra, TutorCafedra.cafedraid == Cafedra.cafedraID)
            .join(TutorPositions, TutorPositions.ID == TutorCafedra.position)
            .where(
                Tutor.TutorID == tutor_id,
                TutorCafedra.deleted == 0,
                Tutor.deleted == 0
            )
            .order_by(TutorCafedra.type)
        )

        result = await self.session.execute(stmt)

        return result.mappings().all()  # вернем как список словарей

    async def get_tutor_ids_having_pps(self, tutor_ids: list[int]) -> set[int]:
        """TutorID, у которых есть хотя бы одна не удалённая запись в tutor_cafedra (ППС)."""
        if not tutor_ids:
            return set()
        stmt = (
            select(Tutor.TutorID)
            .join(TutorCafedra, TutorCafedra.tutorID == Tutor.TutorID)
            .where(
                Tutor.TutorID.in_(tutor_ids),
                TutorCafedra.deleted == 0,
                Tutor.deleted == 0,
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        return {int(row[0]) for row in result.all()}

    async def get_faculty_and_cafedra_managers(self, tutor_id: int):
        stmt = (
            select(
                Cafedra.cafedraManager,
                Faculty.facultyDean
            )
            .join(Tutor, TutorCafedra.tutorID == Tutor.TutorID)
            .join(Cafedra, TutorCafedra.cafedraid == Cafedra.cafedraID)
            .join(Faculty, Faculty.FacultyID == Cafedra.FacultyID)
            .where(
                Tutor.TutorID == tutor_id,
                TutorCafedra.deleted == 0
            )
        )

        result = await self.session.execute(stmt)

        return result.mappings().all()

    async def get_tutor_actions_barrier_by_date(self, tutor_id: int, target_date: datetime.date):
        if self.session_perco is None:
            raise Exception("Sessions are not initialized")

        # 1. Получаем данные из Perco
        stmt_perco = (
            select(
                Personcontrol.controlid,
                Personcontrol.inoutdata,
                Personcontrol.type,
                Control.buildingid,
                Personcontrol.createdate
            )
            .join(Personcontrol, Personcontrol.turniketid == Control.turniketid)
            .where(
                func.date(Personcontrol.createdate) == target_date,
                Personcontrol.personid == tutor_id
            )
            .order_by(Personcontrol.createdate)
        )

        perco_result = await self.session_perco.execute(stmt_perco)
        perco_rows = perco_result.mappings().all()

        if not perco_rows:
            return []

        # 2. Собираем уникальные buildingid
        building_ids = list({row["buildingid"] for row in perco_rows if row["buildingid"] is not None})

        # 3. Получаем данные по зданиям из другой БД (Nitro)
        stmt_nitro = (
            select(Building.buildingID, Building.buildingName, Building.address)
            .where(Building.buildingID.in_(building_ids))
        )

        nitro_result = await self.session.execute(stmt_nitro)
        buildings = nitro_result.mappings().all()

        # Преобразуем в словарь для быстрого доступа
        buildings_dict = {b["buildingID"]: {"buildingName": b["buildingName"], "address": b["address"]} for b in buildings}

        # 4. Объединяем данные
        final_result = []
        for row in perco_rows:
            binfo = buildings_dict.get(row["buildingid"], {"buildingName": None, "address": None})
            final_result.append({
                "id": row["controlid"],
                "inout_data": row["inoutdata"],
                "access_type": row["type"],
                "building_name": binfo["buildingName"],
                "address": binfo["address"],
                "time": row["createdate"].strftime("%H:%M") if row["createdate"] else None
            })

        return final_result

    async def get_tutors_with_positions_by_ids(self, tutor_ids: list[int]):
        stmt = (
            select(Tutor, TutorPositions)
            .outerjoin(TutorPositions, TutorPositions.ID == Tutor.job_title_int)
            .where(Tutor.TutorID.in_(tutor_ids), Tutor.deleted == 0)
        )
        result = await self.session.execute(stmt)
        return result.tuples().all()

    async def join_structural_subdivision_and_tutor_positions(
            self,
            filters: dict = None,
            fields: Sequence | None = None
    ):
        stmt = (
            select(
                Tutor,
                StructuralSubdivision,
                TutorPositions
            )
            .join(StructuralSubdivision, StructuralSubdivision.id == Tutor.departmentid)
            .join(TutorPositions, TutorPositions.ID == Tutor.job_title_int)
        )

        if fields:
            grouped = defaultdict(list)
            for col in fields:
                grouped[col.class_].append(col)

            for model, cols in grouped.items():
                stmt = stmt.options(load_only(*cols))

        if filters:
            for field, values in filters.items():
                if isinstance(values, list):
                    stmt = stmt.where(field.in_(values))
                else:
                    stmt = stmt.where(field == values)

        result = await self.session.execute(stmt)

        rows = cast(list[tuple[Tutor, StructuralSubdivision]], result.tuples().all())

        return rows

    async def join_structural_subdivision_and_tutor_positions_deans(
            self,
            filters: dict = None,
            fields: Sequence | None = None
    ) -> list[tuple[Tutor, StructuralSubdivision]]:
        stmt = (
            select(
                Tutor,
                StructuralSubdivision,
                TutorPositions
            )
            .outerjoin(StructuralSubdivision, StructuralSubdivision.dean == Tutor.TutorID)
            .outerjoin(TutorPositions, TutorPositions.ID == Tutor.job_title_int)
        )

        if fields:
            grouped = defaultdict(list)
            for col in fields:
                grouped[col.class_].append(col)

            for model, cols in grouped.items():
                stmt = stmt.options(load_only(*cols))

        if filters:
            for field, values in filters.items():
                if isinstance(values, list):
                    stmt = stmt.where(field.in_(values))
                else:
                    stmt = stmt.where(field == values)

        result = await self.session.execute(stmt)

        rows = cast(list[tuple[Tutor, StructuralSubdivision]], result.tuples().all())

        return rows
