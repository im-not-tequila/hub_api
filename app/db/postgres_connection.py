from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine, AsyncSession

from app.core.settings import get_settings
from app.core.ssh_postgres_port import get_ssh_postgres_local_port


settings = get_settings()

if settings.ssh_enabled:
    host = "127.0.0.1"
    port = get_ssh_postgres_local_port()
else:
    host = settings.PG_HOST
    port = settings.PG_PORT
user = settings.PG_USER
password = settings.PG_PASSWORD
database = settings.PG_DATABASE

DATABASE_URL = f'postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}'

engine_postgres = create_async_engine(
    DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=3600,
    pool_size=10, max_overflow=20,
)

async_session_postgres = async_sessionmaker(
    engine_postgres, expire_on_commit=False
)

class PostgresBase(DeclarativeBase):
    pass
