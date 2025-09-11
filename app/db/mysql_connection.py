from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.settings import get_settings


settings = get_settings()

host = settings.MYSQL_HOST
port = settings.MYSQL_PORT
user = settings.MYSQL_USER
password = settings.MYSQL_PASSWORD
database = settings.MYSQL_DATABASE

DATABASE_URL = f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}"

engine_mysql = create_async_engine(DATABASE_URL, echo=True)

async_session_mysql = async_sessionmaker(
    engine_mysql, expire_on_commit=False
)

class MySQLBase(DeclarativeBase):
    pass
