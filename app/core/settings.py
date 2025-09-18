from typing import ClassVar
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    model_config = {
        "env_file": Path(__file__).resolve().parent.parent.parent / ".env",
        "env_file_encoding": "utf-8"
    }

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str

    PG_HOST: str
    PG_PORT: int
    PG_USER: str
    PG_PASSWORD: str
    PG_DATABASE: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    REDIS_DATABASE: int

    CURRENT_DIRECTORY: ClassVar[Path] = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIRECTORY: ClassVar[Path] = CURRENT_DIRECTORY / "storage"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.STORAGE_DIRECTORY.exists():
            self.STORAGE_DIRECTORY.mkdir(parents=True)

def get_settings() -> Settings:
    return Settings()
