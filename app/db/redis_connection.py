import redis.asyncio as redis

from app.core.settings import get_settings
from app.core.ssh_redis_port import get_ssh_redis_local_port


settings = get_settings()

host = settings.REDIS_HOST
port = settings.REDIS_PORT

if settings.ssh_enabled:
    host = "127.0.0.1"
    port = get_ssh_redis_local_port()

redis_client = redis.StrictRedis(host=host,
                                 port=port,
                                 db=settings.REDIS_DATABASE,
                                 password=settings.REDIS_PASSWORD,
                                 decode_responses=True)
