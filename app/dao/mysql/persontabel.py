from sqlalchemy import select
from app.dao.base import MySQLDao
from app.models.mysql.perco import Persontabel

class PersontabelDAO(MySQLDao):
    def __init__(self, session):
        super().__init__(session, Persontabel)

    async def get_tutor_working_hours(self, start_date, finish_date, person_id: int):
        """
        Получить сумму часов по каждому дню в диапазоне дат.
        Формат результата: [{ "date": date, "hoursum": float }, ...]
        """
        stmt = (
            select(
                Persontabel.tabelid.label("id"),
                Persontabel.curdate.label("date"),
                Persontabel.hoursum.label("working_hours")
            )
            .where(Persontabel.curdate >= start_date)
            .where(Persontabel.curdate <= finish_date)
            .group_by(Persontabel.curdate)
            .order_by(Persontabel.curdate.asc())
        ).where(Persontabel.personid == person_id)

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {"id": row.id, "date": row.date, "working_hours": float(row.working_hours) if row.working_hours is not None else 0.0}
            for row in rows
        ]
