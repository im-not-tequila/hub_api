import datetime
from fastapi import HTTPException

from app.dao.postgres import NotificationDAO
from app.db.session import get_postgres_session, get_mysql_session
from app.dao.mysql import TutorDAO, PersontabelDAO
from app.models.postgres import (
    User as UserModel,
)


class UserService:
    async def visit_history_barrier(self, user: UserModel, target_date: datetime.date):
        if user.is_student:
            raise HTTPException(status_code=403, detail="Access denied for students")

        async with get_mysql_session('perco') as mysql_session_perco:
            async with get_mysql_session() as mysql_session_nitro:
                actions = await TutorDAO(mysql_session_nitro, mysql_session_perco).get_tutor_actions_barrier_by_date(user.platonus_id, target_date)

            return actions

    async def visit_history_working_hours(self, user: UserModel, start_date: datetime.date, finish_date: datetime.date):
        if user.is_student:
            raise HTTPException(status_code=403, detail="Access denied for students")

        async with get_mysql_session(db_name="perco") as mysql_session:
            dao = PersontabelDAO(mysql_session)
            working_hours = await dao.get_tutor_working_hours(
                start_date=start_date,
                finish_date=finish_date,
                person_id=user.platonus_id
            )

            return working_hours

    async def notifications(self, user_id: int, limit: int = 50):
        async with get_postgres_session() as postgres_session:
            notifications = await NotificationDAO(postgres_session).get_all_filtered(
                filters={
                    "user_id": user_id,
                },
                limit=limit,
            )
            print()
            print(user_id)
            print('111111111111111111111111111111111111111111111')
            print(notifications)

            return notifications

