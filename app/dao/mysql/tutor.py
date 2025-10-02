import hashlib

from typing import cast

from app.dao.base import MySQLDao
from app.models.mysql import Tutor, TutorCafedra, Cafedra, TutorPositions, Faculty
from app.models.mysql.structural_subdivision import StructuralSubdivision
from sqlalchemy import select


class TutorDAO(MySQLDao):
    def __init__(self, session):
        super().__init__(session, Tutor)

    async def get_by_iin(self, iin: str) -> Tutor:
        stmt = select(Tutor).where(Tutor.iinplt == iin)
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_by_platonus_credentials(self, login: str, password: str):
        md5_hash = hashlib.md5()
        md5_hash.update(password.encode('utf-8'))
        md5_password = md5_hash.hexdigest()

        stmt = select(Tutor).where(Tutor.Login == login, Tutor.Password == md5_password)
        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_tutors_and_position(
            self, filters: dict = None
    ) -> list[tuple[Tutor, StructuralSubdivision]]:
        stmt = (
            select(
                Tutor,
                StructuralSubdivision,
            )
            .join(StructuralSubdivision, StructuralSubdivision.dean == Tutor.TutorID)
        )

        if filters:
            for field, values in filters.items():
                if isinstance(values, list):
                    stmt = stmt.where(field.in_(values))
                else:
                    stmt = stmt.where(field == values)

        result = await self.session.execute(stmt)

        rows = cast(list[tuple[Tutor, StructuralSubdivision]], result.tuples().all())

        return rows

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

