from typing import ClassVar, Optional
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
    MYSQL_DATABASE_NITRO: str
    MYSQL_DATABASE_PERCO: str

    PG_HOST: str
    PG_PORT: int
    PG_USER: str
    PG_PASSWORD: str
    PG_DATABASE: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    REDIS_DATABASE: int

    DEBUG: bool = False
    COOKIE_DOMAIN: Optional[str] = None  # None = localhost, ".shakarim.kz" = prod
    SSO_SECRET: Optional[str] = None     # Общий секрет для SSO с PHP-проектом

    # 👉 Добавляем опциональные SSH-настройки
    SSH_HOST: Optional[str] = None
    SSH_PORT: Optional[int] = None
    SSH_USER: Optional[str] = None
    SSH_KEY_PATH: Optional[str] = None
    SSH_PASSWORD: Optional[str] = None

    CURRENT_DIRECTORY: ClassVar[Path] = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIRECTORY: ClassVar[Path] = CURRENT_DIRECTORY / "storage"
    GOOGLE_PLAY_APP_LINK: ClassVar[str] = "https://play.google.com/store/apps/details?id=com.nureek2001.ShakarimApp&pcampaignid=web_share"
    APP_STORE_APP_LINK: ClassVar[str] = "https://apps.apple.com/kz/app/shakarim-university/id6753332756"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.STORAGE_DIRECTORY.exists():
            self.STORAGE_DIRECTORY.mkdir(parents=True)

    @property
    def ssh_enabled(self) -> bool:
        """
        Возвращает True, если заданы SSH-параметры
        """
        return (
            self.SSH_HOST is not None
            and self.SSH_USER is not None
            and (self.SSH_KEY_PATH is not None or self.SSH_PASSWORD is not None)
        )


def get_settings() -> Settings:
    return Settings()
