import json
from time import time
from typing import List

from app.db.redis_connection import redis_client
from app.db.postgres_connection import async_session_postgres
from app.dao.postgres import NotificationDAO
from app.db.session import get_postgres_session

from app.models.postgres import (
    Notification as NotificationModel
)


class NotificationService:
    @staticmethod
    async def send_notification(
            recipient_user_id: int,
            message: str,
            sender_user_id: int | None = None,
            sender_name: str = 'Система',
            title: str = 'Новое уведомление',
            other_data: dict | None = None
    ):
        async with async_session_postgres() as session:
            await NotificationDAO(session).add(
                recipient_user_id=recipient_user_id,
                sender_user_id=sender_user_id,
                sender_name=sender_name,
                title=title,
                message=message,
                other_data=other_data
            )

        payload = {
            "new_notification": True,
            "timestamp": time()
        }

        await redis_client.publish(f"notifications:{recipient_user_id}", json.dumps(payload))

    @staticmethod
    async def notifications(user_id: int, is_read, limit: int = 50):
        async with get_postgres_session() as postgres_session:
            filters = {
                    NotificationModel.recipient_user_id: user_id,
                }

            if is_read is not None:
                filters[NotificationModel.is_read] = is_read

            return await NotificationDAO(postgres_session).get_all_filtered(
                filters=filters,
                limit=limit,
                order_by="created_at:desc"
            )

    @staticmethod
    async def mark_as_read(user_id: int, notification_ids: List[int]):
        async with get_postgres_session() as postgres_session:
            await NotificationDAO(postgres_session).update(
                filters={
                    NotificationModel.recipient_user_id: user_id,
                    NotificationModel.id: notification_ids,
                },
                values={
                    NotificationModel.is_read: True
                }
            )

            payload = {
                "new_notification": True,
                "timestamp": time()
            }

            await redis_client.publish(f"notifications:{user_id}", json.dumps(payload))
