from sqlalchemy import text

from app.dao.base import MySQLDao
from app.models.mysql.nitro import StructuralSubdivision


class StructuralSubdivisionDAO(MySQLDao):
    def __init__(self, session):
        super().__init__(session, StructuralSubdivision)

    async def get_subordinates(self, subdivision_id: int, name_field: str) -> list[dict]:
        query = text(f"""
            WITH RECURSIVE sub_tree AS (
                SELECT id, pre, {name_field} AS name
                FROM structural_subdivision
                WHERE id = :subdivision_id AND deleted = 0

                UNION ALL

                SELECT s.id, s.pre, s.{name_field} AS name
                FROM structural_subdivision s
                JOIN sub_tree st ON s.pre = st.id
                WHERE s.deleted = 0
            )
            SELECT id, name FROM sub_tree
        """)
        result = await self.session.execute(query, {"subdivision_id": subdivision_id})
        return [dict(row._mapping) for row in result.fetchall()]
