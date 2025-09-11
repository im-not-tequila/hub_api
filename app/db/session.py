from contextlib import asynccontextmanager
from .postgres_connection import async_session_postgres
from .mysql_connection import async_session_mysql
from .redis_connection import redis_client


@asynccontextmanager
async def get_postgres_session():
    async with async_session_postgres() as session:
        yield session

@asynccontextmanager
async def get_mysql_session():
    async with async_session_mysql() as session:
        yield session

def get_redis_client():
    return redis_client
