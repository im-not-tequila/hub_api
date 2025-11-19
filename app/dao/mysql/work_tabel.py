from sqlalchemy import select, and_, text, bindparam

from app.dao.base import MySQLDao
from app.models.mysql.nitrosgu import Tabelshtat, TutorStructuralsubdivision
from app.models.mysql.nitro import Tutor, TutorPositions, StructuralSubdivision
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ЖК количество отработанных дней
# ЖЖК количество пропущенных дней
# tabelshtat.rate - ставка (половина / полная)


class WorkTabelDAO(MySQLDao):
    def __init__(self, session_nitro: AsyncSession):
        super().__init__(session_nitro, Tabelshtat)

    async def get_tutors_by_subdivision(self, subdivision_id: int, year: int, month: int):
        query = text("""
                     SELECT DISTINCT tutors.TutorID,
                                     tutors.lastname,
                                     tutors.firstname,
                                     tutors.patronymic,
                                     structural_subdivision.namekz AS subdivision_name,
                                     structural_subdivision.dean,
                                     tutor_positions.Namekz        AS position_name,
                                     tabelshtat.rate
                     FROM nitrosgu.tabelshtat
                              INNER JOIN nitro.tutors ON tabelshtat.tutorid = tutors.TutorID
                              INNER JOIN nitro.structural_subdivision
                                         ON tabelshtat.subdivisionid = structural_subdivision.id
                              INNER JOIN nitro.tutor_positions ON tutor_positions.ID = tabelshtat.`position`
                     WHERE YEAR (tabelshtat.dates) = :year
                       AND MONTH (tabelshtat.dates) = :month
                       AND tabelshtat.subdivisionid = :subdivision_id
                       AND tabelshtat.typestr = 1;
                     """)

        result = await self.session.execute(
            query,
            {"year": year, "month": month, "subdivision_id": subdivision_id},
        )

        return [dict(row._mapping) for row in result.fetchall()]

    async def get_hours_sum_per_day(self, subdivision_id: int, tutor_ids: list[int], year: int, month: int):
        query = text("""
                     SELECT 
                         tabelid  AS tabel_id,
                         personid AS tutor_id,
                         hoursum  AS hour_sum, 
                         DAY (curdate) AS tabel_day, 
                         type AS tabel_type
                     FROM perco.persontabel
                     WHERE YEAR (curdate) = :year
                       AND MONTH (curdate) = :month
                       AND personid IN :tutor_ids
                       AND ID_podrazd = :subdivision_id
                     ORDER BY tabel_day;
                     """)

        query = query.bindparams(
            bindparam("tutor_ids", expanding=True),
            bindparam("year"),
            bindparam("month"),
            bindparam("subdivision_id"),
        )

        result = await self.session.execute(
            query,
            {"tutor_ids": tutor_ids, "year": year, "month": month, "subdivision_id": subdivision_id},
        )

        return [dict(row._mapping) for row in result.fetchall()]
