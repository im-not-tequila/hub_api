from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.settings import get_settings


settings = get_settings()

host = settings.MYSQL_HOST
port = settings.MYSQL_PORT
user = settings.MYSQL_USER
password = settings.MYSQL_PASSWORD
database_nitro = settings.MYSQL_DATABASE_NITRO
database_perco = settings.MYSQL_DATABASE_PERCO

if settings.ssh_enabled:
    host = "127.0.0.1"
    port = 3307

DATABASE_URL_NITRO = f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database_nitro}"
DATABASE_URL_PERCO = f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database_perco}"
DATABASE_URL_NITROSGU = f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database_perco}"

engine_mysql_nitro = create_async_engine(
    DATABASE_URL_NITRO, echo=False, pool_pre_ping=True, pool_recycle=3600,
    pool_size=10, max_overflow=20,
)
engine_mysql_perco = create_async_engine(
    DATABASE_URL_PERCO, echo=False, pool_pre_ping=True, pool_recycle=3600,
    pool_size=10, max_overflow=20,
)
engine_mysql_nitrosgu = create_async_engine(
    DATABASE_URL_NITROSGU, echo=False, pool_pre_ping=True, pool_recycle=3600,
    pool_size=10, max_overflow=20,
)

async_session_mysql_nitro = async_sessionmaker(
    engine_mysql_nitro, expire_on_commit=False
)

async_session_mysql_perco = async_sessionmaker(
    engine_mysql_perco, expire_on_commit=False
)

async_session_mysql_nitrosgu = async_sessionmaker(
    engine_mysql_nitrosgu, expire_on_commit=False
)


class NitroBase(DeclarativeBase):
    pass


class PercoBase(DeclarativeBase):
    pass


class NitrosguBase(DeclarativeBase):
    pass
