from contextlib import asynccontextmanager
from .postgres_connection import async_session_postgres
from .mysql_connection import async_session_mysql_nitro, async_session_mysql_perco, async_session_mysql_nitrosgu
from .redis_connection import redis_client


async def get_postgres_session():
    async with async_session_postgres() as session:
        yield session

async def get_nitro_session():
    async with async_session_mysql_nitro() as session:
        yield session

async def get_perco_session():
    async with async_session_mysql_perco() as session:
        yield session

async def get_nitrosgu_session():
    async with async_session_mysql_nitrosgu() as session:
        yield session

def get_redis_client():
    return redis_client
