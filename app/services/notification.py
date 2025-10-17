import json
import datetime

from app.db.redis_connection import redis_client
from app.db.postgres_connection import async_session_postgres
from app.dao.postgres import NotificationDAO


async def send_notification(user_id: int, message: str, link: str = None):
    print('send_notification')
    payload = {
        "message": message,
        "link": link,
        "read": False,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }

    async with async_session_postgres() as session:
        await NotificationDAO(session).add(
            user_id=user_id,
            message=message,
            link=link
        )

    await redis_client.publish(f"notifications:{user_id}", json.dumps(payload))
