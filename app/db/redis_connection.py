import redis.asyncio as redis

from app.core.settings import get_settings


settings = get_settings()

redis_client = redis.StrictRedis(host=settings.REDIS_HOST,
                                 port=settings.REDIS_PORT,
                                 db=settings.REDIS_DATABASE,
                                 password=settings.REDIS_PASSWORD,
                                 decode_responses=True)
