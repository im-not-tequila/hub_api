import json
from time import time
from typing import List

from app.db.redis_connection import redis_client
from app.dao.postgres import NotificationDAO

from app.models.postgres import (
    Notification as NotificationModel
)
from sqlalchemy.ext.asyncio import AsyncSession


class NotificationService:
    def __init__(self, session_postgres: AsyncSession):
        self.session_postgres = session_postgres

    async def send_notification(
            self,
            recipient_user_id: int,
            message: str,
            sender_user_id: int | None = None,
            sender_name: str = 'Система',
            title: str = 'Новое уведомление',
            other_data: dict | None = None
    ):
        await NotificationDAO(self.session_postgres).add(
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

    async def notifications(self, user_id: int, is_read, limit: int = 50):
        filters = {
                NotificationModel.recipient_user_id: user_id,
            }

        if is_read is not None:
            filters[NotificationModel.is_read] = is_read

        return await NotificationDAO(self.session_postgres).get_all_filtered(
            filters=filters,
            limit=limit,
            order_by="created_at:desc"
        )

    async def mark_as_read(
            self,
            user_id: int,
            notification_ids: List[int]
    ):
        await NotificationDAO(self.session_postgres).update(
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
