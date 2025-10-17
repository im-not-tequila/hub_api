from contextlib import asynccontextmanager
from .postgres_connection import async_session_postgres
from .mysql_connection import async_session_mysql_nitro, async_session_mysql_perco
from .redis_connection import redis_client


@asynccontextmanager
async def get_postgres_session():
    async with async_session_postgres() as session:
        yield session

@asynccontextmanager
async def get_mysql_session(db_name: str = "nitro"):
    if db_name == "nitro":
        async with async_session_mysql_nitro() as session:
            yield session
    elif db_name == "perco":
        async with async_session_mysql_perco() as session:
            yield session
    else:
        raise ValueError("Invalid db_name")

def get_redis_client():
    return redis_client
