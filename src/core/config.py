import os
from typing import Optional

from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env.example"),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Database settings
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DATABASE_URL: Optional[PostgresDsn] = None

    @computed_field
    def database_url(self) -> PostgresDsn:
        """Generate database URL if not provided directly"""
        if self.DATABASE_URL is not None:
            return self.DATABASE_URL

        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=int(self.DB_PORT),
            path=self.DB_NAME,
        )

    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    # Logging settings
    LOG_LEVEL: str = "INFO"

    # Analysis settings
    BATCH_SIZE: int = 100
    MAX_WORKERS: int = 4


settings = Settings()
